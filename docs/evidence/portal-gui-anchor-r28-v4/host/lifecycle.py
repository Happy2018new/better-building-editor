"""Precisely own one immutable dry-card verification client and its cleanup."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from status_reader import read_json as read_status_json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT / '.runtime/projects/portal-r28-gui-anchor-v4'
OWNER = 'portal-r28-gui-anchor-v4'
PROJECT = ROOT / '.runtime/projects/portal-r28-gui-anchor-v4'
SCRIPTS = PROJECT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from _session import process_identity, registry_dir


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf8')


def now():
    return datetime.now(timezone.utc).isoformat()


def memory():
    class Performance(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in
            ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
             'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
            (key, wintypes.DWORD) for key in ('HandleCount', 'ProcessCount', 'ThreadCount')]
    api = ctypes.WinDLL('psapi', use_last_error=True)
    api.GetPerformanceInfo.argtypes = (ctypes.POINTER(Performance), wintypes.DWORD)
    api.GetPerformanceInfo.restype = wintypes.BOOL
    info = Performance()
    info.cb = ctypes.sizeof(info)
    if not api.GetPerformanceInfo(ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'committed_bytes': info.CommitTotal * info.PageSize,
            'limit_bytes': info.CommitLimit * info.PageSize,
            'headroom_bytes': (info.CommitLimit - info.CommitTotal) * info.PageSize}


def handles(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return None
    try:
        count = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return count.value
    finally:
        kernel.CloseHandle(handle)


def process_snapshot():
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
        '@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress'],
        text=True, encoding='utf8').strip()
    pids = json.loads(raw) if raw else []
    if isinstance(pids, int):
        pids = [pids]
    return [{'pid': pid, 'identity': process_identity(pid)} for pid in pids]


def binding():
    launch = json.loads((HERE / 'launch-v2/launch.json').read_bytes())
    path = Path(launch['session_file'])
    row = json.loads(path.read_bytes())
    assert row['owner'] == OWNER and Path(row['project']).resolve() == PROJECT.resolve()
    return path, row


def stop(reason='verification_finished'):
    path, row = binding()
    target = HERE / ('stop-v2-' + str(time.time_ns()))
    target.mkdir()
    report = {'owner': OWNER, 'session_file': str(path), 'binding': row, 'reason': reason,
              'started_at': now(), 'grace_seconds': 45, 'force_executed': False}
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'),
               'stop', '--session', str(path), '--owner', OWNER]
    started = time.monotonic()
    result = subprocess.run(command, cwd=ROOT, capture_output=True,
                            text=True, encoding='utf8', errors='replace', timeout=35)
    report['ordinary_stop'] = {'returncode': result.returncode,
                               'stdout': result.stdout, 'stderr': result.stderr}
    write(target / 'stop.json', report)
    samples = []
    while time.monotonic() - started < 45:
        active = {key: process_identity(row[key + '_pid']) for key in ('game', 'mcdk')}
        samples.append({'at': now(), 'actual_active_creation_identities': active})
        if all(value is None for value in active.values()):
            break
        time.sleep(.5)
    report['grace_samples'] = samples
    exact = {key: process_identity(row[key + '_pid']) for key in ('game', 'mcdk')}
    report['after_grace_active_identity'] = exact
    if any(value is not None for value in exact.values()):
        assert time.monotonic() - started >= 45, 'Full grace is mandatory before force'
        assert all(value is None or value == row[key + '_identity'] for key, value in exact.items())
        # Frozen terminate_owned checks creation identity AND STILL_ACTIVE on the same handle.
        from _session import terminate_owned
        for key, value in exact.items():
            if value is not None:
                terminate_owned(row[key + '_pid'], value)
                report['force_executed'] = True
        write(target / 'stop.json', report)
    # Finalize only this exact registry after independent absence, preserving ordinary failure.
    final = {key: process_identity(row[key + '_pid']) for key in ('game', 'mcdk')}
    assert all(value is None for value in final.values()), final
    finalized = subprocess.run(command, cwd=ROOT, capture_output=True,
                               text=True, encoding='utf8', errors='replace', timeout=35)
    report['registry_finalize'] = {'returncode': finalized.returncode,
                                   'stdout': finalized.stdout, 'stderr': finalized.stderr}
    report['independent_final_active_identity'] = final
    report['registry_final'] = json.loads(path.read_bytes())
    report['finished_at'] = now()
    write(target / 'stop.json', report)
    print(json.dumps({'report': str(target / 'stop.json'), 'force_executed': report['force_executed'],
                      'ordinary_returncode': result.returncode, 'final_active_identity': final}))


def start():
    from assigned_manifest_read import AssignedManifestReader
    manifest_read_events=[]
    assigned_reader=AssignedManifestReader(OWNER,PROJECT,process_identity,manifest_read_events)
    target = HERE / 'launch-v2'
    target.mkdir()
    hosts = json.loads((HERE / 'host-binding-final.json').read_bytes())
    assert all(hashlib.sha256((HERE/key).read_bytes()).hexdigest()==value
               for key,value in hosts['files'].items())
    manifest = json.loads((HERE / 'source-manifest.json').read_bytes())
    assert all(hashlib.sha256((HERE/key).read_bytes()).hexdigest()==value for key,value in manifest.get('local_host_files',{}).items())
    assert all(hashlib.sha256((PROJECT / key).read_bytes()).hexdigest() == expected for key, expected in manifest['host_files'].items())
    assert manifest['owner'] == OWNER
    external = json.loads((HERE / 'external-host-binding.json').read_bytes())
    assert all(hashlib.sha256((ROOT/key).read_bytes()).hexdigest()==value
               for key,value in external.items())
    watch = read_status_json(HERE / 'assert-watch/status.json')
    assert (datetime.now(timezone.utc)-datetime.fromisoformat(watch['checked_at'])).total_seconds()<60
    assert watch['owners']==[OWNER]
    assert watch['host_sha256']==external['.runtime/round-20261023/water-anchor-watcher-v7/watch_owned_disabled_skin_assert_r28_v7.py']
    assert not watch['errors'] and not watch['other_assertions']
    for key, expected in manifest['runtime_files'].items():
        assert hashlib.sha256((PROJECT / key).read_bytes()).hexdigest() == expected, key
    assert hashlib.sha256((PROJECT / '.mcdev.json').read_bytes()).hexdigest() == manifest['mcdev_sha256']
    assert all(manifest['reload_config'][key] is False for key in ('auto_hot_reload_mods','auto_hot_reload_ui','auto_hot_reload_shaders','auto_hot_reload_materials'))
    active = [row for row in process_snapshot() if row['identity'] is not None]
    assert len(active) < 5, active
    assert memory()['headroom_bytes'] >= 6 * 1024**3
    assert not any(json.loads(path.read_bytes()).get('owner') == OWNER
                   for path in registry_dir().glob('*/session.json'))
    executable = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
    guard = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
    exe_sha = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
    guard_sha = '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
    assert hashlib.sha256(executable.read_bytes()).hexdigest() == exe_sha
    assert hashlib.sha256(guard.read_bytes()).hexdigest() == guard_sha
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
               '--project', str(PROJECT), '--owner', OWNER, '--name', OWNER, '--preset', 'ui',
               '--wait', '180', '--mcdk', str(executable), '--noactivate-dll', str(guard),
               '--noactivate-sha256', guard_sha, '--noactivate-mcdk-sha256', exe_sha]
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
    report = {'owner': OWNER, 'project': str(PROJECT), 'command': command, 'started_at': now(),
              'source_manifest_sha256': hashlib.sha256((HERE / 'source-manifest.json').read_bytes()).hexdigest(),
              'preflight_active': active, 'preflight_memory': memory(), 'samples': [],
              'manifest_read_events':manifest_read_events}
    save = lambda: write(target / 'launch.json', report)
    save()
    with (target / 'stdout.json').open('wb') as stdout, (target / 'stderr.txt').open('wb') as stderr:
        launcher = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, creationflags=subprocess.CREATE_NO_WINDOW)
    report['launcher_pid'] = launcher.pid
    report['launcher_identity'] = process_identity(launcher.pid)
    save()
    session_path, observer_started, last, previous = None, False, 0., {}
    try:
        while launcher.poll() is None:
            if session_path is None:
                for path in registry_dir().glob('*/session.json'):
                    row=assigned_reader.read(path,candidate=True)
                    if row is not None:
                        assert Path(row['project']).resolve() == PROJECT.resolve()
                        session_path = path
                        report['session_file'] = str(path)
                        save()
                        break
            if session_path is not None and time.monotonic() - last >= 1.:
                row = assigned_reader.read(session_path)
                sample = {'at': now(), 'state': row.get('state'), 'memory': memory()}
                for key in ('game', 'mcdk'):
                    pid, identity = row.get(key + '_pid'), row.get(key + '_identity')
                    sample[key] = {'pid': pid, 'identity': identity,
                        'handles': handles(pid) if pid and identity and process_identity(pid) == identity else None}
                report['samples'].append(sample)
                save()
                if row.get('game_identity') and not observer_started:
                    with (target / 'observer.stdout.txt').open('wb') as obsout, (target / 'observer.stderr.txt').open('wb') as obserr:
                        observer = subprocess.Popen([sys.executable, '-B', '-X', 'utf8',
                            str(ROOT / '.runtime/round-20261019/watch_exact_start.py'), '--session', str(session_path),
                            '--owner', OWNER, '--project', str(PROJECT), '--output', str(target / 'exact-exit.json')],
                            cwd=ROOT, env=env, stdin=subprocess.DEVNULL, stdout=obsout, stderr=obserr,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                    report['observer_pid'] = observer.pid
                    report['observer_identity'] = process_identity(observer.pid)
                    observer_started = True
                    save()
                invalid = sample['memory']['headroom_bytes'] < 6 * 1024**3
                watcher = read_status_json(HERE / 'assert-watch/status.json')
                if watcher['other_assertions'] or watcher['errors']:
                    report['assertion_guard_failure'] = watcher
                    save()
                    stop('unknown_or_repeated_assertion')
                    raise RuntimeError('Owned assertion guard stopped the session; no new experiment entered')
                for key in ('game', 'mcdk'):
                    value = sample[key]['handles']
                    if value is not None:
                        invalid |= value >= 250000 or key in previous and value - previous[key] >= 10000
                        previous[key] = value
                if invalid:
                    report['resource_guard_failure'] = sample
                    save()
                    stop('resource_guard')
                    raise RuntimeError('Resource guard exceeded; owned session stopped')
                last = time.monotonic()
            time.sleep(.25)
    finally:
        save()
    report['launcher_returncode'] = launcher.returncode
    if launcher.returncode == 0:
        report['result'] = json.loads((target / 'stdout.json').read_bytes())
    save()
    assert launcher.returncode == 0, report
    print(json.dumps({'session_file': report.get('session_file'), 'result': report.get('result')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('start', 'stop'))
    args = parser.parse_args()
    start() if args.operation == 'start' else stop()
