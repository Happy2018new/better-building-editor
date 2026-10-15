"""Start one already-frozen owned portal clone without touching its inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from probe_product_water import snapshot_sources
from _session import load_session, process_identity

parser = argparse.ArgumentParser()
parser.add_argument('--round', default='v3')
args = parser.parse_args()
project = ROOT / ('.runtime/projects/portal-r20-native-' + args.round)
control = ROOT / ('.runtime/portal-native-control-r20-' + args.round)
expected = json.loads((control / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(project) == expected
config = json.loads((project / '.mcdev.json').read_bytes())
assert all(config[key] is False for key in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                         'auto_hot_reload_shaders', 'auto_hot_reload_materials'))
old = load_session('C:/Users/Happy2018new/.pyreact-debug/instances/59d11648f93b4e908b68ed4711c72ba8/session.json', 'portal-r20-native-v1')
assert process_identity(old['game_pid']) is None and process_identity(old['mcdk_pid']) is None
guard = old['noactivation']
for name in ('mcdk', 'dll'):
    assert hashlib.sha256(Path(guard[name]['path']).read_bytes()).hexdigest() == guard[name]['sha256']
command = [sys.executable, '-X', 'utf8', str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
           'start', '--project', str(project), '--owner', 'portal-r20-native-' + args.round,
           '--name', 'portal-r20-native-' + args.round, '--wait', '180', '--preset', 'ui',
           '--game-exe', 'D:/MCStudioDownload/game/MinecraftPE_Netease/3.10.0.420447/Minecraft.Windows.exe',
           '--mcdk', guard['mcdk']['path'], '--noactivate-mcdk-sha256', guard['mcdk']['sha256'],
           '--noactivate-dll', guard['dll']['path'], '--noactivate-sha256', guard['dll']['sha256']]
with (control / 'start.stdout.json').open('x', encoding='utf8') as stdout, (control / 'start.stderr.txt').open('x', encoding='utf8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'), stdout=stdout, stderr=stderr, timeout=300)
assert result.returncode == 0, 'Inspect startup receipt before retrying'
session = json.loads((control / 'start.stdout.json').read_bytes())
receipt = {key: session[key] for key in ('session_file', 'owner', 'state', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity')}
(control / 'ready-summary.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='ascii')
print(json.dumps(receipt))
