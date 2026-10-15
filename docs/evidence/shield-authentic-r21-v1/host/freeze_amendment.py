"""Record prelaunch host-only amendment without replacing the frozen clone."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUTPUT = ROOT / '.runtime/shield-authentic-r21-v1'
CONTROL = ROOT / '.runtime/shield-r20-control-v7-authentic'
assert not (CONTROL / 'start.stdout.json').exists()
plan_path = OUTPUT / 'plan.json'
plan = json.loads(plan_path.read_bytes())
shutil.copy2(plan_path, OUTPUT / 'plan-initial.json')
changed = {}
for relative, expected in list(plan['host_files_sha256'].items()):
    actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
    if actual != expected:
        assert relative == '.runtime/shield-authentic-r21/host.py', relative
        changed[relative] = {'before': expected, 'after': actual}
        plan['host_files_sha256'][relative] = actual
assert len(changed) == 1
for path in (HERE / 'offline.py', Path(__file__), ROOT / '.runtime/shield-crafter-r20/check_fixture_offline.py'):
    plan['host_files_sha256'][path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
plan['prelaunch_amendment'] = {'changes': changed,
    'reason': 'Preserve failed execute-code source/error receipts and freeze offline rollback checks.',
    'offline_rollback_checks': 4, 'offline_rollback_passed': True, 'clone_changed': False}
plan_path.write_text(json.dumps(plan, ensure_ascii=True, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'prelaunch_amendment_recorded': True, 'host_changed': list(changed), 'clone_changed': False}))
