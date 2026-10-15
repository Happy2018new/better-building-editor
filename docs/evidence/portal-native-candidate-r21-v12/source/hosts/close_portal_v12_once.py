"""Make the one normal-close request after the restored six-image attempt."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
report = json.loads((ROOT / '.runtime/portal-native-candidate-observed-r21-v12-json-readback/report.json').read_bytes())
assert all(report[key] for key in ('completed', 'restored', 'source_unchanged'))
assert not report['cleanup_errors'] and len(report['captures']) == 6
ready = json.loads((CONTROL / 'ready-summary.json').read_bytes())
assert ready['owner'] == 'portal-r21-native-candidate-v12'
command = [sys.executable, '-B', '-X', 'utf8',
           str(ROOT / '.agents/skills/pyreact-debugging/scripts/instances.py'),
           'stop', '--session', ready['session_file'], '--owner', ready['owner'], '--wait', '60']
with (CONTROL / 'normal-close.stdout.json').open('x', encoding='utf8') as stdout, (
        CONTROL / 'normal-close.stderr.txt').open('x', encoding='utf8') as stderr:
    result = subprocess.run(command, cwd=ROOT, env=dict(os.environ, OPENBLAS_NUM_THREADS='1'),
                            stdout=stdout, stderr=stderr, timeout=90)
(CONTROL / 'normal-close-result.json').write_text(json.dumps({'returncode': result.returncode,
    'force_used': False, 'normal_close_request_count': 1}, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'normal_close_returncode': result.returncode, 'force_used': False}))
