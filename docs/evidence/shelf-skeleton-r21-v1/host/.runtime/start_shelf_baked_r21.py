"""Freeze or launch the isolated shelf baked-rotation diagnostic once."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path[:0] = [str(SCRIPTS), str(ROOT / 'tools')]
import instances
from census_intrinsic_glint_ui_r21 import commit_at_boundary
from freeze_intrinsic_glint_project_r21 import fingerprint
from probe_product_water import snapshot_sources

PROJECT = ROOT / '.runtime/projects/shelf-r20-baked-v2'
OUTPUT = ROOT / '.runtime/shelf-baked-r21-start-v2'
OWNER = 'root-shelf-r20-baked-v2'


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='ascii')


def live_games():
    command = ("Get-CimInstance Win32_Process -Filter \"Name='Minecraft.Windows.exe'\" | "
               "Where-Object { $_.ExecutablePath } | "
               "Select-Object ProcessId,CreationDate,ExecutablePath | ConvertTo-Json -Compress")
    result = subprocess.run(['powershell', '-NoProfile', '-Command', command],
                            capture_output=True, text=True, check=True, timeout=25,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    value = json.loads(result.stdout) if result.stdout.strip() else []
    return [value] if isinstance(value, dict) else value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--launch', action='store_true')
    args = parser.parse_args()
    files = fingerprint(PROJECT)
    digest = hashlib.sha256(json.dumps(files, ensure_ascii=True).encode('ascii')).hexdigest()
    if not OUTPUT.exists():
        OUTPUT.mkdir()
        save(OUTPUT / 'frozen-project.json', {'project': str(PROJECT), 'files': files,
                                             'files_sha256': digest, 'game_launched': False})
    frozen = json.loads((OUTPUT / 'frozen-project.json').read_bytes())
    if frozen['files'] != files:
        raise RuntimeError('The prepared shelf candidate changed after its freeze')
    if not args.launch:
        print(json.dumps({'prepared': True, 'files': len(files), 'files_sha256': digest}))
        return
    if (OUTPUT / 'launch-attempt.json').exists():
        raise RuntimeError('This private launcher allows exactly one attempt')
    commit, games = commit_at_boundary(), live_games()
    if commit['commit_available_bytes'] < 6 * 1024 ** 3 or len(games) >= 2:
        raise RuntimeError('Resource admission requires 6 GiB commit and fewer than two live games')
    configuration = json.loads((PROJECT / '.mcdev.json').read_bytes())
    if any(configuration.get('auto_hot_reload_' + family) is not False
           for family in ('mods', 'ui', 'materials', 'shaders')):
        raise RuntimeError('Automatic reload must stay disabled')
    save(OUTPUT / 'launch-attempt.json', {'commit': commit, 'live_games': games,
         'source_sha256': snapshot_sources(PROJECT), 'foreground_activation_allowed': False,
         'frozen_files_sha256': digest})
    os.environ['MCDEV_ALLOW_USER_FOREGROUND'] = '1'
    launch = argparse.Namespace(project=str(PROJECT), owner=OWNER, name=None, port=None,
        preset='ui', wait=180, game_exe=configuration['game_executable_path'],
        mcdk=str(ROOT / '.runtime/mcdk-retry-r11/build-ipc-framing-r11/tools/mcdk/mcdk.exe'),
        noactivate_dll=str(ROOT / 'docs/evidence/background-focus-r13-v1/inputs/native_focus_guard.dll'),
        noactivate_sha256='04b073e1aea6fe16a70573e64c6aac31940431409ac90c79f250e02f35a3ec93',
        noactivate_mcdk_sha256='b8eb8959f97a4348006837bb7897d1e5cb957855d1746145974d8f37c00be9f9')
    result = instances.start(launch)
    save(OUTPUT / 'private-start-result.json', result)
    public = {key: result.get(key) for key in ('id', 'owner', 'state', 'session_file',
        'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'error')}
    public['commit_after'] = commit_at_boundary()
    save(OUTPUT / 'start-summary.json', public)
    print(json.dumps(public))


if __name__ == '__main__':
    main()
