"""Cold clone and launch one owned, background shield diagnostic instance."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / 'tools'))
from _session import load_session
from probe_product_water import snapshot_sources, snapshot_digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--round', default='v1')
    parser.add_argument('--native-discovery', action='store_true')
    parser.add_argument('--prepare-only', action='store_true')
    parser.add_argument('--launch-prepared', action='store_true')
    args = parser.parse_args()
    project = ROOT / ('.runtime/projects/shield-r20-' + args.round)
    control = ROOT / ('.runtime/shield-r20-control-' + args.round)
    assert not (args.prepare_only and args.launch_prepared)
    if args.launch_prepared:
        frozen = json.loads((control / 'launch-inputs.json').read_bytes())
        sources = snapshot_sources(project)
        assert frozen['files'] == sources
        assert frozen['source_contract_sha256'] == snapshot_digest(sources)
        assert not (control / 'start.stdout.json').exists()
    else:
        project.mkdir(parents=True, exist_ok=False)
        control.mkdir(parents=True, exist_ok=False)
        for name in ('behavior_pack', 'resource_pack'):
            shutil.copytree(ROOT / name, project / name,
                            ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        shutil.copy2(ROOT / '.mcdev.json', project / '.mcdev.json')
        sources = snapshot_sources(project)
        (control / 'launch-inputs.json').write_text(json.dumps({
            'source_contract_sha256': snapshot_digest(sources), 'files': sources,
            'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            indent=2) + '\n', encoding='ascii')
    if args.prepare_only:
        print(json.dumps({'prepared': True, 'launched': False,
                          'project': str(project), 'control': str(control),
                          'source_contract_sha256': snapshot_digest(sources)}))
        return
    old = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/'
                       '52bceb09152245a1b20b440d012f0f74/session.json',
                       'root-portal-r20-v5')
    guard = old['noactivation']
    for name in ('mcdk', 'dll'):
        assert hashlib.sha256(Path(guard[name]['path']).read_bytes()).hexdigest() == guard[name]['sha256']
    owner = 'shield-r20-' + args.round
    runner = ROOT / '.runtime/shield_instances_native_discovery_r20.py' if args.native_discovery else SCRIPTS / 'instances.py'
    command = [sys.executable, '-X', 'utf8', str(runner), 'start',
               '--project', str(project), '--owner', owner, '--name', owner,
               '--wait', '180', '--preset', 'ui',
               '--game-exe', 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe',
               '--mcdk', guard['mcdk']['path'], '--noactivate-mcdk-sha256', guard['mcdk']['sha256'],
               '--noactivate-dll', guard['dll']['path'], '--noactivate-sha256', guard['dll']['sha256']]
    with (control / 'start.stdout.json').open('w', encoding='utf8') as stdout, \
            (control / 'start.stderr.txt').open('w', encoding='utf8') as stderr:
        result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'),
                                stdout=stdout, stderr=stderr, timeout=300)
    assert result.returncode == 0, 'Inspect owned startup receipt before retrying'
    session = json.loads((control / 'start.stdout.json').read_bytes())
    receipt = {key: session[key] for key in ('session_file', 'owner', 'state', 'game_pid',
                                           'game_identity', 'mcdk_pid', 'mcdk_identity')}
    (control / 'ready-summary.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='ascii')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
