"""Start v10 only after allocation, immediately retaining exact exit handles."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
control = ROOT / '.runtime/portal-native-control-r20-v10'
subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / '.runtime/verify_portal_v10_preflight_r20.py'),
                '--require-commit'], cwd=ROOT, check=True)
subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / '.runtime/start_portal_prepared_r20.py'),
                '--round', 'v10'], cwd=ROOT, check=True, timeout=310)
ready = json.loads((control / 'ready-summary.json').read_bytes())
assert ready['owner'] == 'portal-r20-native-v10' and ready['state'] == 'ready'
subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'tools/watch_intrinsic_glint_exit_r21.py'),
                '--session', ready['session_file'], '--owner', ready['owner'],
                '--output', str(control / 'exact-exit-observation.json')], cwd=ROOT, check=True)
