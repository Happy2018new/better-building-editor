"""Watch one owned child and game with passive process counters only."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time

PROJECT = Path(__file__).resolve().parents[1]
SCRIPTS = PROJECT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from _session import _identity, _kernel, process_identity, registry_dir
from instances import discover, stop as stop_owned
sys.path.insert(0, str(PROJECT / 'tools'))
from probe_liquid_uniform_transport import MemoryCounters


def counters(session):
    kernel = _kernel()
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = (wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD)
    handle = kernel.OpenProcess(0x0410, False, session['game_pid'])
    if not handle:
        raise OSError('Owned game process unavailable')
    try:
        if _identity(kernel, handle) != session['game_identity']:
            raise RuntimeError('Owned game creation identity changed')
        count, memory = wintypes.DWORD(), MemoryCounters()
        memory.cb = ctypes.sizeof(memory)
        if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)) or not psapi.GetProcessMemoryInfo(
                handle, ctypes.byref(memory), memory.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'observed_at': time.time(), 'handles': count.value,
                'working_set_bytes': memory.WorkingSetSize, 'private_commit_bytes': memory.PagefileUsage}
    finally:
        kernel.CloseHandle(handle)


def unsafe(samples, growth_enabled=True):
    if samples[-1]['handles'] >= 100000:
        return 'Absolute native handle cap reached'
    if growth_enabled and len(samples) >= 4 and all(samples[index]['handles'] - samples[index - 1]['handles'] >= 2500
                                 for index in range(len(samples) - 3, len(samples))):
        return 'Native handles grew by at least 2500 in three consecutive five-second intervals'
    return None


def find_owned(owner, started_at):
    rows = []
    for path in registry_dir().glob('*/session.json'):
        value = json.loads(path.read_bytes())
        if value.get('owner') == owner and value.get('created_at', 0) >= started_at - 2:
            rows.append(value)
    if len(rows) > 1:
        raise RuntimeError('More than one newly created exact-owner session')
    return rows[0] if rows else None


BINDING_KEYS = ('id', 'owner', 'project', 'session_file', 'appdata', 'port', 'mcp_url',
                'token', 'game_executable', 'world_path', 'world_link',
                'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')
PUBLISHED_KEYS = frozenset(('world_path', 'world_link', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity'))


def refresh_binding(pinned, allow_publication=False):
    current = json.loads(Path(pinned['session_file']).read_bytes())
    for key in BINDING_KEYS:
        before, after = pinned.get(key), current.get(key)
        if before != after and not (allow_publication and key in PUBLISHED_KEYS and before is None and after is not None):
            raise RuntimeError('Pinned session binding changed: ' + key)
    return current


def safe_binding(session):
    return {key: session.get(key) for key in BINDING_KEYS if key != 'token'}


def observed_identities(session):
    return {kind: process_identity(session[kind + '_pid']) if session.get(kind + '_pid') else None
            for kind in ('game', 'mcdk')}


def cleanup(pinned, row, save):
    journal = {'authorized': True, 'force_used': False, 'pinned_binding': safe_binding(pinned), 'attempts': []}
    row['resource_failure_cleanup'] = journal
    save()
    for force in (False, True):
        exact = pinned
        attempt = {'force': force, 'started_at': time.time(), 'dispatched': False}
        journal['attempts'].append(attempt)
        save()
        try:
            exact = refresh_binding(pinned)
            identities = observed_identities(pinned)
            attempt['identities_before'] = identities
            if any(value is not None and value != pinned.get(kind + '_identity')
                   for kind, value in identities.items()):
                raise RuntimeError('Pinned process creation identity changed before cleanup')
            if not exact.get('game_pid') and identities['mcdk']:
                found = discover(exact['mcdk_pid'], exact['port'], timeout=5)
                if process_identity(exact['mcdk_pid']) != exact['mcdk_identity']:
                    raise RuntimeError('Owned MCDK changed during unpublished child discovery')
                if len(found['children']) > 1:
                    raise RuntimeError('More than one unpublished owned game child')
                attempt['unpublished_discovery'] = found
                if found['children']:
                    if found['listeners'] != [exact['mcdk_pid']]:
                        raise RuntimeError('Unpublished child endpoint owner changed')
                    child = found['children'][0]
                    identity = process_identity(child)
                    if not identity:
                        raise RuntimeError('Unpublished child creation identity unavailable')
                    exact.update(game_pid=child, game_identity=identity)
                    attempt['unpublished_game_binding'] = {'game_pid': child, 'game_identity': identity}
            journal['force_used'] = force
            attempt['target_binding'] = safe_binding(exact)
            save()
            # Pass the pinned data directly; stop never reloads a replacement manifest.
            attempt['dispatched'] = True
            save()
            result = stop_owned(exact, force)
            attempt['result_state'] = result['state']
            attempt['passed'] = True
        except (RuntimeError, TimeoutError, ValueError, OSError, subprocess.TimeoutExpired) as error:
            attempt.update(passed=False, error='%s: %s' % (type(error).__name__, error))
            if isinstance(error, subprocess.TimeoutExpired):
                attempt['discovery_timeout'] = {
                    'command': error.cmd, 'timeout_seconds': error.timeout,
                    'stdout': (error.stdout or b'').decode('utf-8', errors='replace'),
                    'stderr': (error.stderr or b'').decode('utf-8', errors='replace'),
                    'stdout_hex': (error.stdout or b'').hex(),
                    'stderr_hex': (error.stderr or b'').hex()}
            if not attempt['dispatched']:
                journal['refused_binding_drift_or_unknown_child'] = True
                save()
                break
        finally:
            attempt['identities_after'] = observed_identities(exact)
            attempt['finished_at'] = time.time()
            save()
        if not any(attempt['identities_after'].values()):
            break


def run(command, env, timeout, owner, output, session=None, startup_growth_observation_only=False):
    if output.exists():
        raise ValueError('Keep the passive guard receipt fresh')
    started = time.time()
    deadline = time.monotonic() + timeout
    row = {'schema': 1, 'completed': False, 'passed': False, 'read_only_monitor': True,
           'owner': owner, 'started_at': started, 'timeout_seconds': timeout,
           'handle_cap': 100000, 'persistent_growth': {'minimum_delta': 2500, 'interval_seconds': 5, 'intervals': 3},
           'startup_growth_observation_only': startup_growth_observation_only,
           'samples': [], 'observed_session': None, 'failure': None}
    save = lambda: output.write_text(json.dumps(row, indent=2) + '\n', encoding='ascii')
    save()
    pinned = session
    startup_ready_observed = False
    next_sample = 0.
    stdout = stderr = b''
    with subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        row['child_pid'] = process.pid
        save()
        try:
            while process.poll() is None:
                now = time.monotonic()
                if now >= deadline:
                    raise TimeoutError('Fixed child deadline elapsed')
                if now >= next_sample:
                    if pinned is None:
                        session = find_owned(owner, started)
                    else:
                        session = refresh_binding(pinned, allow_publication=True)
                    if session:
                        if session['owner'] != owner or Path(session['project']).resolve() != PROJECT:
                            raise RuntimeError('Passive monitor session ownership changed')
                        pinned = dict(session)
                        row['observed_session'] = safe_binding(pinned)
                        save()
                    if session and session.get('game_pid') and session.get('game_identity'):
                        sample = counters(session)
                        sample['session_ready'] = bool(session.get('ready') and session.get('state') == 'ready')
                        startup_ready_observed = startup_ready_observed or sample['session_ready']
                        sample['growth_stop_enabled'] = not startup_growth_observation_only or startup_ready_observed
                        row['samples'].append(sample)
                        save()
                        eligible = row['samples']
                        if startup_growth_observation_only:
                            eligible = [value for value in eligible if value['growth_stop_enabled']]
                        failure = unsafe([sample], growth_enabled=False) or (unsafe(eligible) if eligible else None)
                        if failure:
                            raise RuntimeError(failure)
                    next_sample = now + 5.
                try:
                    stdout, stderr = process.communicate(timeout=min(.5, max(.01, deadline - time.monotonic())))
                except subprocess.TimeoutExpired:
                    pass
            stdout, stderr = process.communicate()
            if pinned is None:
                pinned = find_owned(owner, started)
            if pinned:
                session = refresh_binding(pinned, allow_publication=True)
                pinned = dict(session)
                row['observed_session'] = safe_binding(pinned)
            if session and session.get('game_pid') and session.get('game_identity'):
                row['terminal_sample'] = counters(session)
                if row['terminal_sample']['handles'] >= 100000:
                    raise RuntimeError('Absolute native handle cap reached at phase completion')
            row.update(completed=True, passed=process.returncode == 0, returncode=process.returncode)
            if process.returncode:
                row.update(failure='Owned child exited with code %s' % process.returncode, failure_kind='child_exit')
        except (RuntimeError, TimeoutError, ValueError, OSError) as error:
            row['failure'] = '%s: %s' % (type(error).__name__, error)
            row['failure_kind'] = 'deadline' if isinstance(error, TimeoutError) else 'health_or_binding'
            process.terminate()
            try:
                stdout, stderr = process.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate(timeout=10)
            row.update(completed=True, returncode=1)
        finally:
            row['finished_at'] = time.time()
            save()
    if row['failure'] and pinned:
        cleanup(pinned, row, save)
    return subprocess.CompletedProcess(command, row['returncode'], stdout, stderr), row
