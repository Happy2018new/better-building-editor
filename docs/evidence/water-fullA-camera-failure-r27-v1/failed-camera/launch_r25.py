"""Cold-launch the reviewed product source while recording startup HANDLEs."""
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

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
OWNER = 'water-r27-merged-fullA-v1'
PROJECT = Path('D:\\Happy2018newの个人文件\\GitHub\\better-building-editor\\.runtime\\projects\\water-r27-merged-flow-editor-v1')
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from _session import process_identity, registry_dir
sys.path.insert(0,str(ROOT/'.runtime/round-20261022/water-anchor-watcher-v5'))
from windows_manifest_reader import native_read_json,bounded_manifest_read
from watch_owned_disabled_skin_assert_r27_v5 import native_load_session


def guarded_json(path,events):
    return bounded_manifest_read(lambda:native_read_json(path),events,str(path))

kernel = ctypes.WinDLL('kernel32', use_last_error=True)
kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
kernel.OpenProcess.restype = wintypes.HANDLE
kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
kernel.CloseHandle.argtypes = (wintypes.HANDLE,)


def handle_count(pid):
    process = kernel.OpenProcess(0x0410, False, pid)
    if not process:
        return None
    try:
        result = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(process, ctypes.byref(result)):
            raise ctypes.WinError(ctypes.get_last_error())
        return result.value
    finally:
        kernel.CloseHandle(process)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', default=OWNER)
    args = parser.parse_args()
    if args.name != OWNER:
        parser.error('This receipt is pinned to the frozen owner')
    import guard_policy
    binding_path = WORK / 'final-source-binding-v1.json'
    binding = json.loads(binding_path.read_bytes())
    assert binding['owner'] == OWNER and Path(binding['project']).resolve() == PROJECT.resolve()
    assert guard_policy.remaining_seconds(binding['guard_deadline_utc']) > 300, 'No time for cold launch and restore'
    host_binding = json.loads((WORK / 'prelaunch-host-binding-v1.json').read_bytes())
    assert hashlib.sha256(binding_path.read_bytes()).hexdigest() == host_binding['source_binding_sha256']
    for name, expected in host_binding['host_sha256'].items():
        assert hashlib.sha256((WORK / name).read_bytes()).hexdigest() == expected, name
    for name, expected in host_binding['external_host_sha256'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    watch = json.loads((WORK / 'assert-watch/status.json').read_bytes())
    assert watch['owners'] == [OWNER] and not watch['errors'] and not watch['other_assertions']
    assert (datetime.now(timezone.utc) - datetime.fromisoformat(watch['checked_at'])).total_seconds() < 5
    assert watch['host_sha256'] == host_binding['external_host_sha256']['.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py']
    for name, expected in binding['auxiliary_sha256'].items():
        assert hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() == expected, name
    launch_inputs = json.loads((WORK / 'product-v2-launch-inputs.json').read_bytes())
    for name, expected in binding['owner_and_qualification_preserved_sha256'].items():
        assert hashlib.sha256((PROJECT / name).read_bytes()).hexdigest() == expected, name
    sys.path.insert(0, str(PROJECT / 'tools'))
    from probe_product_water import snapshot_sources
    assert snapshot_sources(PROJECT) == launch_inputs['source_sha256']
    config = json.loads((PROJECT / '.mcdev.json').read_bytes())
    assert all(config.get(key) is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
    assert hashlib.sha256((Path(binding['archive']['path'])).read_bytes()).hexdigest()==launch_inputs['archive']['sha256']
    out = WORK / 'launch'
    out.mkdir(exist_ok=False)
    mcdk = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
    guard = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
    mcdk_sha = 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
    guard_sha = '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
    for path, expected in ((mcdk, mcdk_sha), (guard, guard_sha)):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected
    manifest_read_events=[]
    for manifest in registry_dir().glob('*/session.json'):
        row = guarded_json(manifest,manifest_read_events)
        if row.get('owner') == OWNER:
            raise ValueError('This owner already has a session')
    command = [sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
               '--project', str(PROJECT), '--owner', OWNER, '--name', OWNER,
               '--preset', 'ui', '--wait', '180', '--mcdk', str(mcdk),
               '--noactivate-dll', str(guard), '--noactivate-sha256', guard_sha,
               '--noactivate-mcdk-sha256', mcdk_sha]
    env = os.environ.copy()
    env.update(OPENBLAS_NUM_THREADS='1', MCDEV_ALLOW_USER_FOREGROUND='0')
    report = {'schema': 1, 'owner': OWNER, 'project': str(PROJECT),
              'launch_inputs_sha256': hashlib.sha256((WORK / 'product-v2-launch-inputs.json').read_bytes()).hexdigest(),
              'source_archive_sha256': launch_inputs['archive']['sha256'],
              'command': command, 'started_at': datetime.now(timezone.utc).isoformat(), 'samples': [],
              'manifest_read_events':manifest_read_events}
    def save():
        (out / 'launch.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    def sample(session, stage):
        row = {'stage': stage, 'sampled_at': datetime.now(timezone.utc).isoformat(),
               'owner': session.get('owner'), 'session_id': session.get('id'),
               'session_state': session.get('state')}
        for key in ('game', 'mcdk'):
            pid, identity = session.get(key + '_pid'), session.get(key + '_identity')
            if not pid or not identity or process_identity(pid) != identity:
                row[key] = {'pid': pid, 'identity_verified': False}
                continue
            row[key] = {'pid': pid, 'identity': identity, 'identity_verified': True,
                        'handles': handle_count(pid)}
        report['samples'].append(row)
        save()
        for kind in ('game', 'mcdk'):
            current = row.get(kind, {}).get('handles')
            previous = next((item.get(kind, {}).get('handles') for item in reversed(report['samples'][:-1])
                             if item.get(kind, {}).get('identity') == row.get(kind, {}).get('identity')
                             and item.get(kind, {}).get('handles') is not None), None)
            if current is not None and (current >= 250000 or previous is not None and current - previous >= 10000):
                report['handle_guard_failure'] = {'kind': kind, 'stage': stage, 'handles': current, 'previous': previous}
                save()
                stop = subprocess.run([sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'),
                    'stop', '--session', str(report['session_file']), '--owner', OWNER],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=45)
                report['guard_stop'] = {'exit_code': stop.returncode, 'stdout': stop.stdout, 'stderr': stop.stderr}
                save()
                raise RuntimeError('Weekend cold startup exceeded fixed handle guard')
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
             'total_pagefile', 'available_pagefile', 'total_virtual', 'available_virtual', 'available_extended')]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    kernel.GlobalMemoryStatusEx.argtypes = (ctypes.POINTER(MemoryStatus),)
    assert kernel.GlobalMemoryStatusEx(ctypes.byref(memory))
    report['memory_preflight'] = {'available_commit_bytes': memory.available_pagefile,
        'minimum_available_commit_bytes': 6 * 1024 ** 3, 'api': 'GlobalMemoryStatusEx'}
    save()
    assert memory.available_pagefile >= 6 * 1024 ** 3, 'Below fixed 6 GiB commit headroom; do not launch'
    raw_pids = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
        "@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"],
        text=True, encoding='utf8')
    process_ids = json.loads(raw_pids) if raw_pids.strip() else []
    if isinstance(process_ids, int):
        process_ids = [process_ids]
    observations = [{'pid': pid, 'live_creation_identity': process_identity(pid)} for pid in process_ids]
    active = [row for row in observations if row['live_creation_identity'] is not None]
    report['single_instance_preflight'] = {'at': datetime.now(timezone.utc).isoformat(),
        'process_observations': observations, 'active_minecraft_count': len(active)}
    report['launcher_host_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['condition_change_sha256'] = hashlib.sha256((WORK / 'stage-r25.json').read_bytes()).hexdigest()
    save()
    assert len(active)<5, 'Five actual live Minecraft cap reached'
    with (out / 'stdout.json').open('wb') as stdout, (out / 'stderr.txt').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                   stdout=stdout, stderr=stderr,
                                   creationflags=subprocess.CREATE_NO_WINDOW)
        report.update(launcher_pid=process.pid, launcher_identity=process_identity(process.pid))
        save()
        session_path = None
        last_sample = 0.
        exact_exit_started = False
        continuous_guard_started = False
        while process.poll() is None:
            if session_path is None:
                for path in registry_dir().glob('*/session.json'):
                    try:
                        row = guarded_json(path,manifest_read_events)
                    except (OSError, ValueError):
                        continue
                    if row.get('owner') != OWNER:
                        continue
                    assert Path(row['project']).resolve() == PROJECT.resolve()
                    session_path = path
                    report['session_file'] = str(path)
                    save()
                    break
            if session_path is not None:
                try:
                    row = bounded_manifest_read(lambda:native_load_session(str(session_path),OWNER),
                        manifest_read_events,str(session_path))
                    assert Path(row['project']).resolve()==PROJECT.resolve()
                except (OSError, ValueError):
                    save()
                    raise
                if row is not None and time.monotonic() - last_sample >= 1.:
                    stage = ('ready' if row.get('state') == 'ready' and row.get('game_identity')
                             else 'game_started' if row.get('game_identity')
                             else 'mcdk_started')
                    for kind in ('game', 'mcdk'):
                        for suffix in ('pid', 'identity'):
                            key = kind + '_' + suffix
                            if row.get(key):
                                report[key] = row[key]
                    sample(row, stage)
                    last_sample = time.monotonic()
                    if row.get('game_identity') and not exact_exit_started:
                        observer = [sys.executable, '-X', 'utf8',
                            str(ROOT / '.runtime/round-20261019/watch_exact_start.py'),
                            '--session', str(session_path), '--owner', OWNER,
                            '--project', str(PROJECT), '--output', str(out / 'exact-exit.json')]
                        with (out / 'observer.stdout.txt').open('wb') as obs_out, \
                                (out / 'observer.stderr.txt').open('wb') as obs_err:
                            observer_process = subprocess.Popen(observer, cwd=ROOT, env=env,
                                stdin=subprocess.DEVNULL, stdout=obs_out, stderr=obs_err,
                                creationflags=subprocess.CREATE_NO_WINDOW)
                        report.update(observer_pid=observer_process.pid,
                                      observer_identity=process_identity(observer_process.pid))
                        save()
                        exact_exit_started = True
                    if (not continuous_guard_started and row.get('game_identity') and row.get('mcdk_identity')):
                        guard_started = subprocess.run([sys.executable, '-X', 'utf8', '-B',
                            str(WORK / 'watch_handles.py'), '--detach'], cwd=ROOT, env=env,
                            capture_output=True, text=True, timeout=15)
                        report['continuous_guard_start'] = {'exit_code': guard_started.returncode,
                            'stdout': guard_started.stdout, 'stderr': guard_started.stderr,
                            'launch_state_at_start': row.get('state')}
                        save()
                        guard_started.check_returncode()
                        continuous_guard_started = True
            time.sleep(.25)
        report['launcher_exit_code'] = process.returncode
        save()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, command)
    result = json.loads((out / 'stdout.json').read_bytes())
    report.update({key: result.get(key) for key in
                   ('state', 'ready', 'session_file', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')})
    save()
    assert continuous_guard_started, 'No continuous guard coverage; refuse stages'
    print(json.dumps({key: report.get(key) for key in
                      ('owner', 'state', 'ready', 'session_file', 'game_pid', 'observer_pid', 'launcher_exit_code')}))


if __name__ == '__main__':
    main()
