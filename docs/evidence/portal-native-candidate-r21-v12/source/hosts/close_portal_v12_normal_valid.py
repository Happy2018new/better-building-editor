"""Issue the single normal close after correcting an unused CLI argument."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
control = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
previous = json.loads((control / 'normal-close-result.json').read_bytes())
assert previous['normal_close_request_count'] == 0 and previous['returncode'] == 2
ready = json.loads((control / 'ready-summary.json').read_bytes())
command = [sys.executable, '-B', '-X', 'utf8',
           str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
           'stop', '--session', ready['session_file'], '--owner', ready['owner']]
with (control / 'actual-normal-close.stdout.json').open('x', encoding='utf8') as stdout, (
        control / 'actual-normal-close.stderr.txt').open('x', encoding='utf8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OPENBLAS_NUM_THREADS='1'),
                            stdout=stdout, stderr=stderr, timeout=60)
(control / 'actual-normal-close-result.json').write_text(json.dumps({'returncode': result.returncode,
    'force_used': False, 'normal_close_request_count': 1}, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'normal_close_returncode': result.returncode, 'force_used': False}))
