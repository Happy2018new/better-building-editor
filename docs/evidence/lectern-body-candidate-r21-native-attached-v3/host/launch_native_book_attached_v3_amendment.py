"""Separate launch amendment; preserve the frozen native-book hosts and clones."""
import os

os.environ['OPENBLAS_NUM_THREADS'] = '1'

import argparse
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import subprocess
import sys
import time

import probe_native_book_oracle_attached_v3 as attached
from _session import _identity, _kernel, load_session, process_identity


ROOT = attached.base.ROOT
HERE = Path(__file__).resolve().parent
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
OUTPUT = HERE / 'native-oracle-attached-v3-launch-amendment-v1'
HOST_SHA256 = 'c4d3fad841f0718bb81cf74aeca93893be892c6d5c3ae917445348a6d691e9fe'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
OBSERVER = ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'
EXPECTED = {
    MCDK: 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9',
    GUARD: '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
    CAPTURE: 'cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8',
    OBSERVER: 'aa436ee9a0f496554c69330d8456fa21b6bb551b63032f0b5a453ad9748646aa',
    ROOT / 'tools/probe_intrinsic_glint_ui_r21.py': '40a840256274d7a95a90cdd1d95e78d0e1502e38823e3f11281b681b5f95885f',
    SCRIPTS / '_session.py': '9bf1400cda12457ec1b3dd2351fed366c10ad069c781565eabb12e45b2431313',
    SCRIPTS / 'instances.py': 'bd8fbeba3145cef771c0abd1859ca9f02520855b1db75e9ef76c7cee232ebfaa',
    SCRIPTS / '_window.py': '9fdb52e92aeb9930d8faffb81ab2023aaec68383b71b6fab9172643270e0826e',
}


def write(path, data):
    with path.open('x', encoding='ascii') as handle:
        handle.write(json.dumps(data, ensure_ascii=True, indent=2) + '\n')


def game_census():
    command = ("@(Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
               'Select-Object ProcessId,ThreadCount,HandleCount) | ConvertTo-Json -Compress')
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
        capture_output=True, timeout=15, check=True,
        creationflags=subprocess.CREATE_NO_WINDOW, env=os.environ.copy())
    rows = json.loads(result.stdout.decode('utf-8-sig').strip() or '[]')
    rows = rows if isinstance(rows, list) else [rows]
    kernel = _kernel()
    live, exited = [], []
    for row in rows:
        pid = int(row['ProcessId'])
        handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
        if not handle:
            error = ctypes.get_last_error()
            if error == 5 and row['ThreadCount'] == 0 and row['HandleCount'] == 0:
                exited.append(dict(row, classification='zero_thread_handle_shell',
                    open_error=error, exit_code_available=False))
                continue
            if error != 87:
                raise OSError(error, 'Cannot establish MC exit/liveness for pid %s' % pid)
            exited.append(dict(row, classification='already_absent', open_error=error))
            continue
        try:
            code = wintypes.DWORD()
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            identity = _identity(kernel, handle)
            if identity is not None:
                live.append(dict(row, identity=identity, classification='live'))
                continue
            if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                raise ctypes.WinError(ctypes.get_last_error())
            assert code.value != 259, 'Unresolved live MC process identity'
            exited.append(dict(row, classification='verified_exited',
                zero_thread_handle_shell=row['ThreadCount'] == 0 and row['HandleCount'] == 0,
                exit_code=code.value, exit_code_hex='0x%08X' % code.value))
        finally:
            kernel.CloseHandle(handle)
    return {'live': live, 'excluded_exited': exited}


def preflight():
    binding = attached.verify()
    assert binding['host_sha256'] == HOST_SHA256
    dependencies = {str(path.relative_to(ROOT)): attached.base.sha(path)
                    for path in EXPECTED}
    assert all(attached.base.sha(path) == digest for path, digest in EXPECTED.items())
    config = json.loads((attached.PROJECT / '.mcdev.json').read_bytes())
    reloads = {key: config[key] for key in ('auto_hot_reload_mods',
        'auto_hot_reload_ui', 'auto_hot_reload_shaders', 'auto_hot_reload_materials')}
    assert all(value is False for value in reloads.values())
    games = game_census()
    memory = attached.base.commit_at_boundary()
    return {'schema': 1, 'binding': binding, 'process_census': games, 'commit': memory,
        'config_sha256': attached.base.sha(attached.PROJECT / '.mcdev.json'),
        'reloads': reloads, 'dependencies': dependencies,
        'amendment_sha256': attached.base.sha(Path(__file__)),
        'openblas_num_threads': os.environ['OPENBLAS_NUM_THREADS'],
        'minimum_commit_gib': 6, 'game_calls': 0, 'launch_count': 0,
        'launch_gate': not games['live'] and memory['commit_available_bytes'] >= 6 * 1024 ** 3}


def launch():
    assert not OUTPUT.exists(), 'Fresh launch output required'
    receipt = preflight()
    assert receipt['launch_gate'], receipt['process_census']
    OUTPUT.mkdir()
    receipt.update(root_scheduled=True, launch_count=1)
    write(OUTPUT / 'prelaunch.json', receipt)
    command = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
        '--project', str(attached.PROJECT), '--owner', attached.OWNER,
        '--mcdk', str(MCDK), '--noactivate-dll', str(GUARD),
        '--noactivate-sha256', EXPECTED[GUARD],
        '--noactivate-mcdk-sha256', EXPECTED[MCDK], '--wait', '180']
    env = os.environ.copy()
    env.update(MCDEV_ALLOW_USER_FOREGROUND='1', OPENBLAS_NUM_THREADS='1')
    with (OUTPUT / 'start.stdout.json').open('xb') as stdout, (OUTPUT / 'start.stderr.txt').open('xb') as stderr:
        result = subprocess.run(command, stdout=stdout, stderr=stderr, env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    raw = json.loads((OUTPUT / 'start.stdout.json').read_bytes())
    summary = {key: raw.get(key) for key in ('id', 'owner', 'session_file', 'state', 'ready',
        'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'error')}
    write(OUTPUT / 'launch-summary.json', dict(summary, launch_returncode=result.returncode))
    print(json.dumps(summary, ensure_ascii=True), flush=True)
    if result.returncode or raw.get('state') != 'ready' or not raw.get('ready'):
        return result.returncode or 1
    session = load_session(raw['session_file'], attached.OWNER, live=True)
    observer_output = OUTPUT / 'exact-process-exit.json'
    observer_command = [sys.executable, '-B', '-X', 'utf8', str(OBSERVER),
        '--session', session['session_file'], '--owner', attached.OWNER,
        '--output', str(observer_output)]
    with (OUTPUT / 'observer.stdout.txt').open('xb') as stdout, (OUTPUT / 'observer.stderr.txt').open('xb') as stderr:
        observer = subprocess.Popen(observer_command, stdout=stdout, stderr=stderr, env=env,
            creationflags=subprocess.CREATE_NO_WINDOW)
    observer_identity = process_identity(observer.pid)
    assert observer_identity is not None
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        if observer.poll() is not None:
            raise RuntimeError('Exact observer exited before acceptance; inspect its private stderr')
        if observer_output.exists():
            try:
                observed = json.loads(observer_output.read_bytes())
            except json.JSONDecodeError:
                time.sleep(.05)
                continue
            assert observed['session'] == session['id'] and observed['owner'] == attached.OWNER
            for kind in ('game', 'mcdk'):
                row = observed['processes'][kind]
                assert row['state'] == 'live'
                assert row['pid'] == session[kind + '_pid']
                assert row['identity'] == session[kind + '_identity']
            ready = dict(summary, observer_pid=observer.pid, observer_identity=observer_identity,
                observer_output=str(observer_output), exact_process_handles_retained=True,
                openblas_num_threads='1', probe_started=False, capture_count=0)
            write(OUTPUT / 'launch-ready.json', ready)
            print(json.dumps(ready, ensure_ascii=True), flush=True)
            return 0
        time.sleep(.05)
    raise TimeoutError('Observer did not retain both exact handles; no capture is authorized')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('preflight')
    check.add_argument('--output', type=Path)
    start = sub.add_parser('launch')
    start.add_argument('--scheduled-by-root', action='store_true', required=True)
    args = parser.parse_args()
    if args.action == 'preflight':
        receipt = preflight()
        if args.output:
            write(args.output, receipt)
        print(json.dumps(receipt, ensure_ascii=True), flush=True)
    else:
        sys.exit(launch())
