"""Start the mesh selector and retain the exact owned process exit handles."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
control = ROOT/'.runtime/shelf-mesh-inputs-r21-start-v1'
subprocess.run([sys.executable, '-B', '-X', 'utf8',
                str(ROOT/'.runtime/start_shelf_mesh_inputs_r21.py'), '--launch'],
               cwd=ROOT, check=True, timeout=240)
ready = json.loads((control/'start-summary.json').read_bytes())
assert ready['state'] == 'ready' and ready['owner'] == 'root-shelf-r20-mesh-inputs-v1'
subprocess.run([sys.executable, '-B', '-X', 'utf8',
               str(ROOT/'tools/watch_intrinsic_glint_exit_r21.py'),
               '--session', ready['session_file'], '--owner', ready['owner'],
               '--output', str(control/'exact-exit.json')], cwd=ROOT, check=True)
