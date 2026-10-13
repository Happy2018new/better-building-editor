import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0, str(SCRIPTS))
from _session import process_identity

SESSION = Path('C:/Users/Happy2018new/.pyreact-debug/instances/d9ea32ce15e04c549c285cc3dbb0c788/session.json')
PREFIX = 'client-anchor-depth-player-r16-v1'
data = json.loads(SESSION.read_bytes())
assert data['owner'] == 'frame-r16-background'
assert Path(data['project']).resolve() == ROOT
assert data['game_pid'] == 6632 and data['game_identity'] == '134363310609599370'
assert data['mcdk_pid'] == 57424 and data['mcdk_identity'] == '134363310607641486'
artifacts = Path(data['artifacts']).resolve(strict=True)
assert artifacts == SESSION.parent / 'artifacts'

def save(label, value):
    path = artifacts / (PREFIX + '.' + label + '.json')
    with path.open('x', encoding='ascii') as output:
        output.write(json.dumps(value, ensure_ascii=True, indent=2) + '\n')

def identities():
    return {name: {'pid': data[name + '_pid'], 'expected_identity': data[name + '_identity'],
                   'observed_identity': process_identity(data[name + '_pid'])}
            for name in ('game', 'mcdk')}

before = identities()
assert all(row['observed_identity'] == row['expected_identity'] for row in before.values()), before
for name in ('session.json', '.mcdev.json', 'mcdk.log', 'prepare.log'):
    target = artifacts / (PREFIX + '.pre-stop.' + name.lstrip('.'))
    assert not target.exists()
    shutil.copyfile(SESSION.parent / name, target)
command = [sys.executable, '-X', 'utf8', str(SCRIPTS / 'instances.py'), 'stop',
           '--session', str(SESSION), '--owner', data['owner']]
started = time.monotonic()
result = subprocess.run(command, cwd=ROOT, capture_output=True, timeout=25)
for stream in ('stdout', 'stderr'):
    path = artifacts / (PREFIX + '.stop.' + stream)
    with path.open('xb') as output:
        output.write(getattr(result, stream))
save('stop', {'command': command, 'returncode': result.returncode,
              'elapsed_seconds': time.monotonic() - started, 'force': False,
              'before': before, 'after': identities()})
for name in ('session.json', 'mcdk.log'):
    target = artifacts / (PREFIX + '.post-stop.' + name)
    assert not target.exists()
    shutil.copyfile(SESSION.parent / name, target)
print(json.dumps({'returncode': result.returncode, 'after': identities()}))
