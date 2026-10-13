"""Run one externally bounded protected door diagnosis in this isolated worktree."""
import argparse
import base64
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
TOTAL_SECONDS = 150
WORK_SECONDS = 110
PROBE_SHA = '6fe41694606a33f6ede15cbccf72f4c4a951dcf424017ce524af1ae0281517a8'
MCDK_SHA = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
GUARD_SHA = 'c22fa0cd0bdbfb7d9218d59573b61619111f9bd180562c9bd51c69276c11c178'
COPY_HASHES = ('e485a7b24e8d5d3c645d1d39ffcfd3cefa6ba5a7f96c1f5c65034e696a43cfba',
               '3e0e8fe912e12eb6448dfbc29ae8908ae2b55d68764b10ac476b588d166f52c3',
               'c3cbfd069298f2971d0041ad08bddcb567bcf23b1804be45204e8aed29231cfc')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def bounded(command, timeout):
    process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        timed_out = False
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate(timeout=3)
        timed_out = True
    return {'returncode': process.returncode, 'stdout': stdout.decode('utf8', errors='replace'),
            'stderr': stderr.decode('utf8', errors='replace'), 'timeout': timed_out,
            'stdout_base64': base64.b64encode(stdout).decode('ascii'),
            'stderr_base64': base64.b64encode(stderr).decode('ascii')}


def restore_inputs(rows):
    errors = []
    for row in reversed(rows):
        try:
            target = Path(row['target'])
            if not row.get('installed'):
                row['restored'] = True
                continue
            if not target.exists() or sha(target) != row['used_sha256']:
                row['restored'] = False
                row['restoration_refused'] = 'Target changed after approved installation'
                raise ValueError('Runtime source target changed externally; restoration refused')
            if row['originally_present']:
                if sha(Path(row['original'])) != row['original_sha256']:
                    raise ValueError('Original-byte backup changed; restoration refused')
                shutil.copyfile(row['original'], target)
                row['restored'] = sha(target) == row['original_sha256']
            else:
                target.unlink(missing_ok=True)
                row['restored'] = not target.exists()
            if not row['restored']:
                errors.append('Restoration hash mismatch: ' + str(target))
        except Exception as error:
            errors.append('%s: %s' % (row['target'], error))
    return errors


def inspect_process(pid):
    from ctypes import wintypes
    import _session
    kernel = _session._kernel()
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                                wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        identity = _session._identity(kernel, handle)
        if identity is None:
            return None
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(handle, 0, path, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        return {'identity': identity, 'executable': path.value}
    finally:
        kernel.CloseHandle(handle)


def complete_cleanup_binding(session):
    """Recover an unpublished game child for cleanup only, retaining the original manifest."""
    if session.get('game_pid') or not session.get('mcdk_pid'):
        return session
    expected_parent = session['mcdk_identity']
    expected_executable = Path(session['noactivation']['mcdk']['path']).resolve()
    parent = inspect_process(session['mcdk_pid'])
    if parent is None or parent['identity'] != expected_parent:
        return session
    if Path(parent['executable']).resolve() != expected_executable:
        raise RuntimeError('Unpublished game parent executable changed; cleanup binding refused')
    command = ("@(Get-CimInstance Win32_Process -Filter 'ParentProcessId=%d' | "
               "Where-Object Name -eq 'Minecraft.Windows.exe' | Select-Object -ExpandProperty ProcessId) "
               "| ConvertTo-Json -Compress") % session['mcdk_pid']
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True,
                            timeout=3, creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError('Unpublished owned game discovery failed')
    candidates = json.loads(result.stdout.decode('utf-8-sig') or '[]')
    candidates = candidates if isinstance(candidates, list) else [candidates]
    live = [(pid, actual) for pid in candidates if (actual := inspect_process(pid)) is not None]
    if inspect_process(session['mcdk_pid']) != parent:
        raise RuntimeError('Owned MCDK changed during unpublished game discovery')
    if len(live) > 1:
        raise RuntimeError('Multiple live unpublished games; cleanup binding requires inspection')
    if not live:
        return dict(session, verified_no_unpublished_live_game=True)
    pid, actual = live[0]
    if (Path(actual['executable']).resolve() != Path(session['game_executable']).resolve() or
            int(actual['identity']) < int(expected_parent)):
        raise RuntimeError('Unpublished game path/creation is not owned expected game')
    return dict(session, game_pid=pid, game_identity=actual['identity'],
                unpublished_game_recovered_for_cleanup_only=True)


def emergency_cleanup(session, owner, output):
    os.environ.update(MCDEV_SESSION_FILE=str(session), MCDEV_OWNER=owner)
    import probe_native_single_door as probe
    report = {'restored': False, 'physical_orientation_accepted': False}
    try:
        with probe.shapes.Client(timeout=2) as client:
            report['server'] = probe.shapes.execute(client, probe.CLEAR % probe.MARKER, True)
            report['restored'] = report['server']['restored']
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    save(output, report)
    return 0 if report['restored'] else 1


def run(directory, shared, owner, name):
    if directory.exists():
        raise ValueError('Supervisor evidence directory must be fresh')
    if ROOT == shared or ROOT.parent.name != '.runtime':
        raise ValueError('Requires this isolated runtime worktree')
    directory.mkdir(parents=True)
    report_path = directory / 'supervisor.json'
    report = {'schema': 1, 'owner': owner, 'name': name, 'project': str(ROOT),
              'started_at': datetime.now(timezone.utc).isoformat(), 'launches': 0,
              'total_limit_seconds': TOTAL_SECONDS, 'work_limit_seconds': WORK_SECONDS,
              'readiness_seconds': 90, 'background_only': True, 'desktop_input': False,
              'physical_orientation_accepted': False, 'phases': [], 'inputs': [], 'cleanup_errors': []}
    session = None
    started = time.monotonic()
    sys.path.insert(0, str(SCRIPTS))
    from _session import process_identity, registry_dir, terminate_owned
    def phase(label, command, timeout):
        if timeout <= 0:
            raise TimeoutError('Supervisor phase budget exhausted: ' + label)
        row = {'label': label, 'command': command, 'timeout_seconds': timeout,
               'started_elapsed_seconds': time.monotonic() - started}
        report['phases'].append(row)
        save(report_path, report)
        row.update(bounded(command, timeout))
        row['finished_elapsed_seconds'] = time.monotonic() - started
        save(report_path, report)
        return row
    try:
        copies = ((SCRIPTS / 'instances.py', shared / '.agents/skills/pyreact-debugging/scripts/instances.py'),
                  (SCRIPTS / 'mcdk.py', shared / '.agents/skills/pyreact-debugging/scripts/mcdk.py'),
                  (ROOT / '.mcdev.json', shared / '.runtime/r11-native/.mcdev.json'))
        executable = shared / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
        guard = shared / '.runtime/worktree-archive-r7/p0-integration/files/.runtime/native_focus_guard-final-r7/native_focus_guard.dll'
        expected = {executable: MCDK_SHA, guard: GUARD_SHA, ROOT / 'tools/probe_native_single_door.py': PROBE_SHA}
        expected.update({source: COPY_HASHES[index] for index, (target, source) in enumerate(copies)})
        for source, expected_sha in expected.items():
            if sha(source) != expected_sha:
                raise ValueError('Approved source hash changed: ' + str(source))
        report['approved_sources'] = {str(source): sha(source) for source in expected}
        save(report_path, report)
        for index, (target, source) in enumerate(copies):
            original, used = directory / ('input-%d-original' % index), directory / ('input-%d-used' % index)
            row = {'target': str(target), 'source': str(source), 'originally_present': target.exists(),
                   'original': str(original), 'used': str(used), 'used_sha256': sha(source)}
            if target.exists():
                shutil.copyfile(target, original)
                row['original_sha256'] = sha(original)
            report['inputs'].append(row)
            save(report_path, report)
            shutil.copyfile(source, used)
            shutil.copyfile(used, target)
            row['installed'] = True
            save(report_path, report)
        for relative in ('tools/probe_native_single_door.py', 'tools/capture_native_state_transform_shapes.py',
                         '.agents/skills/pyreact-debugging/scripts/_session.py'):
            shutil.copyfile(ROOT / relative, directory / Path(relative).name)
        shutil.copyfile(Path(__file__), directory / 'supervisor-used.py')
        query = bounded(['powershell', '-NoProfile', '-Command',
            'Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id | ConvertTo-Json -Compress'], 8)
        report['game_process_query'] = query
        if query['timeout'] or query['returncode']:
            raise RuntimeError('Cannot establish live game limit')
        pids = json.loads(query['stdout']) if query['stdout'].strip() else []
        if isinstance(pids, int):
            pids = [pids]
        report['live_games_before'] = [{'pid': pid, 'identity': identity} for pid in pids
                                       if (identity := process_identity(pid)) is not None]
        if len(report['live_games_before']) >= 5:
            raise RuntimeError('Maximum five live games; no slot available')
        existing = []
        for path in registry_dir().glob('*/session.json'):
            data = json.loads(path.read_bytes())
            if data.get('name') == name and data.get('owner') == owner and Path(data['project']).resolve() == ROOT:
                existing.append(str(path))
        if existing:
            raise ValueError('Supervisor owner/name requires a fresh session: ' + repr(existing))
        report['launches'] = 1
        launch = phase('launch', [sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
            '--project', str(ROOT), '--owner', owner, '--name', name, '--mcdk', str(executable),
            '--noactivate-dll', str(guard), '--noactivate-sha256', GUARD_SHA,
            '--noactivate-mcdk-sha256', MCDK_SHA, '--wait', '90'], WORK_SECONDS - (time.monotonic() - started))
        if launch['stdout'].strip():
            (directory / 'launch-original.json').write_bytes(base64.b64decode(launch['stdout_base64']))
            session = json.loads(launch['stdout'])
        if launch['timeout'] or launch['returncode'] or not session or not session.get('ready'):
            raise RuntimeError('Protected launch failed before door diagnosis')
        shutil.copyfile(Path(session['session_file']).parent / '.mcdev.json', directory / 'generated-config.json')
        probe = phase('probe', [sys.executable, '-X', 'utf8', str(ROOT / 'tools/probe_native_single_door.py'),
            str(directory / 'probe.json'), '--session', session['session_file'], '--owner', owner],
            WORK_SECONDS - (time.monotonic() - started))
        if probe['timeout'] or probe['returncode']:
            raise RuntimeError('Door diagnostic failed or remained unverified')
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    finally:
        if session is None:
            for path in registry_dir().glob('*/session.json'):
                data = json.loads(path.read_bytes())
                if data.get('name') == name and data.get('owner') == owner and Path(data['project']).resolve() == ROOT:
                    session = data
                    break
        if session:
            try:
                session = complete_cleanup_binding(session)
            except Exception as error:
                report['cleanup_errors'].append('Unpublished owned game discovery: ' + str(error))
            report['session'] = {key: session.get(key) for key in ('id', 'session_file', 'owner', 'project',
                                  'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity',
                                  'unpublished_game_recovered_for_cleanup_only',
                                  'verified_no_unpublished_live_game')}
            diagnosis = {}
            try:
                probe_path = directory / 'probe.json'
                diagnosis = json.loads(probe_path.read_bytes()) if probe_path.exists() else {}
            except Exception as error:
                report['cleanup_errors'].append('Diagnostic receipt: ' + str(error))
            report['diagnosis'] = {key: diagnosis.get(key, False) for key in
                ('completed', 'restored', 'server_exact_native_pair', 'data_replication_verified',
                 'client_typed_pair_verified', 'physical_orientation_accepted', 'mutation_attempted')}
            if (diagnosis.get('mutation_attempted') and diagnosis.get('restored') is not True or
                    any(row['label'] == 'probe' for row in report['phases']) and not diagnosis):
                try:
                    report['emergency_cleanup'] = phase('emergency_cleanup', [sys.executable, '-X', 'utf8',
                        str(Path(__file__)), '--cleanup-session', session['session_file'], '--owner', owner,
                        '--cleanup-output', str(directory / 'emergency-cleanup.json')],
                        min(8, TOTAL_SECONDS - (time.monotonic() - started) - 25))
                except Exception as error:
                    report['cleanup_errors'].append('Emergency fixture cleanup: ' + str(error))
            command = [sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'stop',
                       '--session', session['session_file'], '--owner', owner]
            try:
                report['normal_stop'] = phase('normal_stop', command,
                                              min(16, TOTAL_SECONDS - (time.monotonic() - started) - 9))
            except Exception as error:
                report['cleanup_errors'].append('Normal session stop: ' + str(error))
            try:
                alive = [kind for kind in ('game', 'mcdk') if session.get(kind + '_pid') and
                         process_identity(session[kind + '_pid']) == session.get(kind + '_identity')]
                if alive:
                    report['inspected_live_owned_kinds'] = alive
                    if session.get('unpublished_game_recovered_for_cleanup_only'):
                        report['recovered_force_stop'] = []
                        for kind in alive:
                            terminate_owned(session[kind + '_pid'], session[kind + '_identity'])
                            report['recovered_force_stop'].append({'kind': kind, 'pid': session[kind + '_pid'],
                                                                 'identity': session[kind + '_identity']})
                            save(report_path, report)
                    else:
                        report['force_stop'] = phase('force_stop', command + ['--force'],
                                                     min(8, TOTAL_SECONDS - (time.monotonic() - started) - 1))
                report['identities_after_stop'] = {kind: process_identity(session[kind + '_pid'])
                    if session.get(kind + '_pid') else None for kind in ('game', 'mcdk')}
                report['owned_processes_absent'] = (bool(session.get('game_pid') or
                    session.get('verified_no_unpublished_live_game')) and
                    all(value is None for value in report['identities_after_stop'].values()))
                if not session.get('game_pid') and not session.get('verified_no_unpublished_live_game'):
                    report['cleanup_errors'].append('Unpublished game binding unresolved; process absence unverified')
                shutil.copyfile(session['session_file'], directory / 'session-stopped.json')
            except Exception as error:
                report['cleanup_errors'].append('Owned process verification/force stop: ' + str(error))
        report['cleanup_errors'].extend(restore_inputs(report['inputs']))
        report['elapsed_seconds'] = time.monotonic() - started
        report['within_total_limit'] = report['elapsed_seconds'] <= TOTAL_SECONDS
        report['ok'] = (not report.get('error') and not report['cleanup_errors'] and
                        report.get('owned_processes_absent') is True and report['within_total_limit'] and
                        report.get('diagnosis', {}).get('data_replication_verified') is True)
        save(report_path, report)
    print(json.dumps({key: report.get(key) for key in ('ok', 'error', 'elapsed_seconds', 'within_total_limit',
                     'diagnosis', 'owned_processes_absent', 'cleanup_errors')}))
    return 0 if report['ok'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', nargs='?', type=Path)
    parser.add_argument('--shared-root', type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--name')
    parser.add_argument('--cleanup-session', type=Path)
    parser.add_argument('--cleanup-output', type=Path)
    args = parser.parse_args()
    if args.cleanup_session:
        return emergency_cleanup(args.cleanup_session, args.owner, args.cleanup_output)
    if not args.directory or not args.shared_root or not args.name:
        parser.error('Run requires directory, --shared-root and a fresh --name')
    return run(args.directory.resolve(), args.shared_root.resolve(), args.owner, args.name)


if __name__ == '__main__':
    raise SystemExit(main())
