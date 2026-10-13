"""Bound child termination and exact owned stop by the ready-phase outer deadline."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import time

from _session import _identity, _kernel, process_identity
from _window import _list_windows, user32
from liquid_passive_guard_r12_v8 import (counters, unsafe, refresh_binding, safe_binding,
                                       observed_identities, find_owned, discover, PROJECT)


def terminate_exact(pid, identity, deadline):
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000 | 0x1 | 0x100000, False, int(pid))
    if not handle:
        if process_identity(pid) is not None:
            raise RuntimeError('Cannot open the exact owned process for termination')
        return
    try:
        current = _identity(kernel, handle)
        if current is None:
            return
        if current != identity:
            raise RuntimeError('Process creation identity changed; refusing termination')
        if not kernel.TerminateProcess(handle, 1):
            raise ctypes.WinError(ctypes.get_last_error())
        kernel.WaitForSingleObject(handle, int(max(0., min(1., deadline - time.time())) * 1000))
    finally:
        kernel.CloseHandle(handle)


def cleanup(pinned, row, save, deadline):
    journal = {'authorized': True, 'force_used': False, 'pinned_binding': safe_binding(pinned),
               'outer_deadline_unix': deadline, 'attempts': []}
    row['resource_failure_cleanup'] = journal
    try:
        exact = refresh_binding(pinned)
        identities = observed_identities(exact)
        if any(value is not None and value != exact.get(key + '_identity') for key, value in identities.items()):
            raise RuntimeError('Exact creation binding changed before cleanup')
        journal['identities_before'] = identities
        if not exact.get('game_pid') and identities['mcdk']:
            remaining = deadline - time.time()
            if remaining <= 3.:
                raise TimeoutError('No bounded reserve for unpublished owned child discovery')
            found = discover(exact['mcdk_pid'], exact['port'], timeout=min(1., remaining - 3.))
            journal['unpublished_discovery'] = found
            if (process_identity(exact['mcdk_pid']) != exact['mcdk_identity']
                    or len(found['children']) > 1
                    or found['children'] and found['listeners'] != [exact['mcdk_pid']]):
                raise RuntimeError('Unpublished child endpoint/ownership changed; refusing stop')
            if found['children']:
                child = found['children'][0]
                identity = process_identity(child)
                if not identity:
                    raise RuntimeError('Unpublished owned child identity unavailable')
                exact.update(game_pid=child, game_identity=identity)
                identities['game'] = identity
        if identities['game']:
            user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
            for window in _list_windows():
                if window['pid'] == exact['game_pid']:
                    user32.PostMessageW(window['hwnd'], 0x0010, 0, 0)
            journal['ordinary_close_sent'] = True
            stop_deadline = min(time.time() + 6., deadline - 3.)
            while time.time() < stop_deadline and process_identity(exact['game_pid']) == exact['game_identity']:
                time.sleep(min(.1, max(0., stop_deadline - time.time())))
        for key in ('game', 'mcdk'):
            if exact.get(key + '_pid') and process_identity(exact[key + '_pid']) == exact.get(key + '_identity'):
                journal['force_used'] = True
                journal['attempts'].append({'force': True, 'kind': key, 'pid': exact[key + '_pid']})
                terminate_exact(exact[key + '_pid'], exact[key + '_identity'], deadline)
        journal['identities_after'] = observed_identities(exact)
        if any(journal['identities_after'].values()):
            raise RuntimeError('Owned process still live after bounded stop')
        exact.update(state='stopped', ready=False)
        link = Path(exact['world_link']) if exact.get('world_link') else None
        if link and link.is_junction() and link.resolve() == Path(exact['world_path']).resolve():
            link.rmdir()
        Path(exact['session_file']).write_text(json.dumps(exact, indent=2) + '\n', encoding='ascii')
        journal['passed'] = True
    except Exception as error:
        journal.update(passed=False, error='%s: %s' % (type(error).__name__, error))
    finally:
        journal['finished_at'] = time.time()
        journal['outer_deadline_met'] = time.time() <= deadline
        save()


def run(command, env, timeout, owner, output, session=None, outer_deadline=None,
        startup=False, growth_enabled=True):
    if output.exists():
        raise ValueError('Fresh passive phase receipt required')
    started_at = time.time()
    outer_deadline = outer_deadline if outer_deadline is not None else started_at + 240.
    deadline = min(started_at + timeout, outer_deadline - 12.)
    row = {'schema': 1, 'completed': False, 'passed': False, 'read_only_monitor': True,
           'owner': owner, 'timeout_seconds': timeout, 'outer_deadline_unix': outer_deadline,
           'samples': [], 'failure': None, 'observed_session': safe_binding(session) if session else None,
           'persistence_errors': []}
    row.update(startup=startup, growth_enabled=growth_enabled)
    def save():
        try:
            output.write_text(json.dumps(row, indent=2) + '\n', encoding='ascii')
        except OSError as error:
            row['persistence_errors'].append(str(error))
    save()
    stdout = stderr = b''
    process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    row.update(child_pid=process.pid, started_at=time.time())
    next_sample = 0.
    try:
        while process.poll() is None:
            if time.time() >= deadline:
                raise TimeoutError('Fixed child deadline elapsed')
            if time.time() >= next_sample:
                if session is None:
                    session = find_owned(owner, started_at)
                elif startup:
                    session = refresh_binding(session, allow_publication=True)
                else:
                    refresh_binding(session)
                if session:
                    if session['owner'] != owner or Path(session['project']).resolve() != PROJECT:
                        raise RuntimeError('Passive startup ownership changed')
                    row['observed_session'] = safe_binding(session)
                    if startup and session.get('game_identity'):
                        created_at = int(session['game_identity']) / 10000000. - 11644473600.
                        outer_deadline = min(started_at + 240., created_at + 240.)
                        deadline = min(deadline, created_at + 180.)
                        row.update(game_created_at_unix=created_at, startup_deadline_unix=created_at + 180.,
                                   outer_deadline_unix=outer_deadline)
                failure = None
                if session and session.get('game_pid') and session.get('game_identity'):
                    sample = counters(session)
                    row['samples'].append(sample)
                    failure = unsafe(row['samples'], growth_enabled=growth_enabled)
                save()
                if failure:
                    raise RuntimeError(failure)
                next_sample = time.time() + 5.
            try:
                stdout, stderr = process.communicate(timeout=min(.25, max(.01, deadline - time.time())))
            except subprocess.TimeoutExpired:
                pass
        stdout, stderr = process.communicate(timeout=max(.01, min(1., outer_deadline - time.time())))
        if startup:
            session = refresh_binding(session, allow_publication=True) if session else find_owned(owner, started_at)
            row['observed_session'] = safe_binding(session) if session else None
        if session and session.get('game_pid') and session.get('game_identity'):
            row['terminal_sample'] = counters(session)
            if row['terminal_sample']['handles'] >= 100000:
                raise RuntimeError('Absolute native handle cap reached at phase completion')
        row.update(returncode=process.returncode, passed=process.returncode == 0)
        if process.returncode:
            raise RuntimeError('Owned child exited with code %s' % process.returncode)
    except Exception as error:
        row.update(failure='%s: %s' % (type(error).__name__, error), returncode=1, passed=False)
        if process.poll() is None:
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=max(.01, min(1., outer_deadline - time.time())))
            except subprocess.TimeoutExpired:
                process.kill()
                try:
                    stdout, stderr = process.communicate(timeout=max(.01, min(1., outer_deadline - time.time())))
                except subprocess.TimeoutExpired:
                    row['child_termination_unproven'] = True
        if session is None:
            session = find_owned(owner, started_at)
        if session:
            cleanup(session, row, save, outer_deadline)
    finally:
        row.update(completed=True, finished_at=time.time())
        save()
    if row['persistence_errors']:
        row.update(passed=False, returncode=1)
    return subprocess.CompletedProcess(command, row['returncode'], stdout, stderr), row
