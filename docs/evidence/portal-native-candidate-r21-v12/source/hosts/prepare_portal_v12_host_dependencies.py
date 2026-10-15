"""Discover missing host imports offline, then freeze only those source files."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/portal-r21-native-candidate-v12'
CONTROL = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
DEPENDENCIES = ROOT / '.runtime/portal-native-candidate-host-dependencies-r21-v12'
assert not DEPENDENCIES.exists()
sys.path[:0] = [str(PROJECT / '.agents/skills/pyreact-debugging/scripts'), str(PROJECT / 'tools'), str(ROOT / 'tools')]
import mcdk


def no_runtime(*args, **kwargs):
    raise AssertionError('This dependency discovery forbids RPC and WGC')


mcdk.Client.call = no_runtime
import capture_native_window
capture_native_window.capture = no_runtime
import probe_portal_native_candidate_r21
from probe_product_water import snapshot_digest, snapshot_sources

frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(PROJECT) == frozen
rows = {}
for module in tuple(sys.modules.values()):
    name = getattr(module, '__file__', None)
    if not name:
        continue
    source = Path(name).resolve()
    if source.suffix != '.py' or not source.is_relative_to(ROOT) or source.is_relative_to(PROJECT):
        continue
    relative = source.relative_to(ROOT).as_posix()
    if not (relative.startswith('tools/') or relative.startswith('.agents/skills/pyreact-debugging/scripts/')):
        continue
    assert not (PROJECT / relative).exists(), relative
    target = DEPENDENCIES / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    rows[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
assert rows
report = {'schema': 1, 'scope': 'Pure host import completion; no product or clone bytes changed',
          'source_contract_sha256': snapshot_digest(frozen), 'files': rows,
          'discovery_rpc_forbidden': True, 'discovery_wgc_forbidden': True,
          'first_capture_attempt': 'Import failed before Client construction or output creation',
          'runner_sha256': hashlib.sha256((ROOT / '.runtime/run_portal_v12_frozen_host_dependencies.py').read_bytes()).hexdigest(),
          'original_host_sha256': hashlib.sha256((ROOT / '.runtime/portal_native_candidate_host_r21_v12.py').read_bytes()).hexdigest()}
(CONTROL / 'host-dependency-amendment.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps(report))
