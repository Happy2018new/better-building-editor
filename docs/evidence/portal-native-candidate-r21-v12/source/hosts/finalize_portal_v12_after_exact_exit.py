"""Finalize metadata only after both retained exact identities have exited."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
control = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import process_identity
ready = json.loads((control / 'ready-summary.json').read_bytes())
observed = json.loads((control / 'exact-exit-observation.json').read_bytes())
assert observed['completed']
for kind in ('game', 'mcdk'):
    assert observed['processes'][kind]['state'] == 'exited'
    assert process_identity(ready[kind + '_pid']) != ready[kind + '_identity']
command = [sys.executable, '-B', '-X', 'utf8',
           str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
           'stop', '--session', ready['session_file'], '--owner', ready['owner']]
with (control / 'finalize.stdout.json').open('x', encoding='utf8') as stdout, (
        control / 'finalize.stderr.txt').open('x', encoding='utf8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OPENBLAS_NUM_THREADS='1'),
                            stdout=stdout, stderr=stderr, timeout=30)
assert result.returncode == 0
session = json.loads((control / 'finalize.stdout.json').read_bytes())
assert session['state'] == 'stopped' and session['ready'] is False
summary = {'returncode': result.returncode, 'state': session['state'], 'ready': session['ready'],
           'both_exact_identities_absent_before_finalize': True,
           'normal_close_request_count': 1, 'force_used': False,
           'game_exit_code': observed['processes']['game']['exit_code_hex'],
           'mcdk_exit_code': observed['processes']['mcdk']['exit_code_hex'],
           'normal_exit_accepted': False, 'runtime_released': True}
(control / 'finalize-summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps(summary))
