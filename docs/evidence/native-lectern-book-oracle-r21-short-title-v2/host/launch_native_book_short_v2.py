"""One authorized cold noactivation launch, with private raw startup output."""
import json
import os
from pathlib import Path
import subprocess
import sys

import probe_native_book_oracle_short_v2 as short
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from _session import process_identity


ROOT = short.oracle.ROOT
HERE = Path(__file__).resolve().parent
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
OUTPUT = HERE / 'native-oracle-short-v2-launch'
MCDK = ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'
GUARD = ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'
CAPTURE = ROOT / '.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'


def main():
    assert not OUTPUT.exists(), 'Fresh launch output required'
    binding = short.verify()
    assert binding['host_sha256'] == 'd701942a46dbb18dcc0438e985e5aeb152605f83716bd3b80300f37151851a72'
    paths = [MCDK, GUARD, CAPTURE, ROOT / 'tools/watch_intrinsic_glint_exit_r21.py',
             ROOT / 'tools/probe_intrinsic_glint_ui_r21.py',
             SCRIPTS / '_session.py', SCRIPTS / 'instances.py', SCRIPTS / '_window.py']
    dependencies = {str(path.relative_to(ROOT)): short.oracle.sha(path) for path in paths}
    assert short.oracle.sha(MCDK) == 'b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9'
    assert short.oracle.sha(GUARD) == '04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93'
    assert short.oracle.sha(CAPTURE) == short.oracle.SINGLE_FRAME_SHA256
    command = "@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress"
    found = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                           capture_output=True, timeout=15, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW)
    pids = json.loads(found.stdout.decode('utf-8-sig').strip() or '[]')
    pids = pids if isinstance(pids, list) else [pids]
    games = [{'pid': pid, 'identity': identity} for pid in pids
             if (identity := process_identity(pid)) is not None]
    assert not games, games
    memory = commit_at_boundary()
    assert memory['commit_available_bytes'] >= 6 * 1024 ** 3, memory
    preflight = {'schema': 1, 'binding': binding, 'real_games': games, 'commit': memory,
                 'config_sha256': short.oracle.sha(short.oracle.PROJECT / '.mcdev.json'),
                 'dependencies': dependencies, 'minimum_commit_gib': 6,
                 'mc_wgc_authorized_by_root': True, 'launch_count': 1}
    OUTPUT.mkdir()
    (OUTPUT / 'prelaunch.json').write_text(json.dumps(preflight, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    launch = [sys.executable, '-B', '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'start',
              '--project', str(short.oracle.PROJECT), '--owner', short.oracle.OWNER,
              '--mcdk', str(MCDK), '--noactivate-dll', str(GUARD),
              '--noactivate-sha256', short.oracle.sha(GUARD),
              '--noactivate-mcdk-sha256', short.oracle.sha(MCDK), '--wait', '180']
    env = os.environ.copy()
    env['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    with (OUTPUT / 'start.stdout.json').open('xb') as stdout, (OUTPUT / 'start.stderr.txt').open('xb') as stderr:
        result = subprocess.run(launch, stdout=stdout, stderr=stderr, env=env,
                                creationflags=subprocess.CREATE_NO_WINDOW)
    print(json.dumps({'launch_returncode': result.returncode, 'output': str(OUTPUT)}), flush=True)
    raw = json.loads((OUTPUT / 'start.stdout.json').read_bytes())
    print(json.dumps({key: raw.get(key) for key in
        ('id', 'owner', 'session_file', 'state', 'ready', 'game_pid', 'game_identity',
         'mcdk_pid', 'mcdk_identity', 'error')}, ensure_ascii=True), flush=True)
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
