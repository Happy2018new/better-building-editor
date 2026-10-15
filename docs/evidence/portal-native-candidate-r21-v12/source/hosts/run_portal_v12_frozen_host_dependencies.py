"""Validate the amended import closure offline, or run its six-image attempt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/portal-r21-native-candidate-v12'
CONTROL = ROOT / '.runtime/portal-native-candidate-control-r21-v12'
DEPENDENCIES = ROOT / '.runtime/portal-native-candidate-host-dependencies-r21-v12'
OUTPUT = ROOT / '.runtime/portal-native-candidate-observed-r21-v12'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=('validate', 'capture'))
args = parser.parse_args()
manifest = json.loads((CONTROL / 'host-dependency-amendment.json').read_bytes())
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == manifest['runner_sha256']
assert hashlib.sha256((ROOT / '.runtime/portal_native_candidate_host_r21_v12.py').read_bytes()).hexdigest() == manifest['original_host_sha256']
assert {p.relative_to(DEPENDENCIES).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in DEPENDENCIES.rglob('*.py')} == manifest['files']
sys.path[:0] = [str(PROJECT / '.agents/skills/pyreact-debugging/scripts'), str(PROJECT / 'tools'),
               str(DEPENDENCIES / 'tools'), str(DEPENDENCIES / '.agents/skills/pyreact-debugging/scripts')]
import mcdk
if args.action == 'validate':
    def no_runtime(*unused_args, **unused_kwargs):
        raise AssertionError('Offline import forbids RPC or WGC')
    mcdk.Client.call = no_runtime
    import capture_native_window
    capture_native_window.capture = no_runtime
import probe_portal_native_candidate_r21 as probe
from probe_product_water import snapshot_digest, snapshot_sources
frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(PROJECT) == frozen
assert snapshot_digest(frozen) == manifest['source_contract_sha256']
loaded = {}
for module in tuple(sys.modules.values()):
    name = getattr(module, '__file__', None)
    if not name:
        continue
    path = Path(name).resolve()
    if path.suffix != '.py' or not path.is_relative_to(ROOT):
        continue
    if path == Path(__file__).resolve():
        continue
    assert path.is_relative_to(PROJECT) or path.is_relative_to(DEPENDENCIES), str(path)
    loaded[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
receipt = {'action': args.action, 'source_contract_sha256': manifest['source_contract_sha256'],
           'loaded_host_sources': loaded, 'unfrozen_live_root_tools_imported': False,
           'rpc_calls_at_import': 0, 'wgc_calls_at_import': 0, 'qualification': False}
path = CONTROL / ('amended-' + args.action + '-import.json')
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'offline_import_passed': True, 'host_source_count': len(loaded),
                  'added_dependency_count': len(manifest['files']), 'action': args.action}), flush=True)
if args.action == 'capture':
    assert (CONTROL / 'amended-validate-import.json').exists() and not OUTPUT.exists()
    ready = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    probe.run(argparse.Namespace(project=PROJECT, session=ready['session_file'], owner=ready['owner'], output=OUTPUT))
