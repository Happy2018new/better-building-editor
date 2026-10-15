"""Keep the frozen probe, transporting its deep document readback as JSON."""
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
OUTPUT = ROOT / '.runtime/portal-native-candidate-observed-r21-v12-json-readback'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('action', choices=('validate', 'capture'))
args = parser.parse_args()
amendment = json.loads((CONTROL / 'json-readback-host-amendment.json').read_bytes())
assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == amendment['runner_sha256']
base = json.loads((CONTROL / 'host-dependency-amendment.json').read_bytes())
assert hashlib.sha256((ROOT / '.runtime/run_portal_v12_frozen_host_dependencies.py').read_bytes()).hexdigest() == base['runner_sha256']
assert {p.relative_to(DEPENDENCIES).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in DEPENDENCIES.rglob('*.py')} == base['files']
sys.path[:0] = [str(PROJECT / '.agents/skills/pyreact-debugging/scripts'), str(PROJECT / 'tools'),
               str(DEPENDENCIES / 'tools'), str(DEPENDENCIES / '.agents/skills/pyreact-debugging/scripts')]
import mcdk
if args.action == 'validate':
    def no_runtime(*unused_args, **unused_kwargs):
        raise AssertionError('Offline validation forbids RPC or WGC')
    mcdk.Client.call = no_runtime
    import capture_native_window
    capture_native_window.capture = no_runtime
import probe_portal_native_candidate_r21 as probe
from probe_product_water import snapshot_digest, snapshot_sources
frozen = json.loads((CONTROL / 'launch-inputs.json').read_bytes())['files']
assert snapshot_sources(PROJECT) == frozen
assert snapshot_digest(frozen) == amendment['source_contract_sha256']
loaded = {}
for module in tuple(sys.modules.values()):
    name = getattr(module, '__file__', None)
    if not name:
        continue
    path = Path(name).resolve()
    if path.suffix != '.py' or not path.is_relative_to(ROOT) or path == Path(__file__).resolve():
        continue
    assert path.is_relative_to(PROJECT) or path.is_relative_to(DEPENDENCIES), str(path)
    loaded[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
first = json.loads((ROOT / '.runtime/portal-native-candidate-observed-r21-v12/report.json').read_bytes())
assert not first['captures'] and first['restored'] and first['source_unchanged'] and not first['cleanup_errors']
original_run = probe.CandidateCheck.run


def prepare_readback_code(code):
    marker = "_result={'source':s.editor.document.to_data(),'profile':s.portal_profile.identity}"
    if marker in code:
        code += '\n_result=json.dumps(_result)\n'
    return code


def json_readback(check, code):
    return original_run(check, prepare_readback_code(code))


def has_transport_placeholder(value):
    if isinstance(value, dict):
        return ('__repr__' in value and '__type__' in value) or any(has_transport_placeholder(v) for v in value.values())
    if isinstance(value, (tuple, list)):
        return any(has_transport_placeholder(v) for v in value)
    return False


probe.CandidateCheck.run = json_readback
fixtures = []
if args.action == 'validate':
    for family in probe.FAMILIES:
        data = probe.document(family)
        payload = {'source': data, 'profile': [1, '3.10.0.420447', 'native_ray_planes_candidate_r21', 128]}
        class OfflineClient:
            def call(self, tool, parameters):
                assert tool == 'execute_code' and parameters['direct_return']
                assert parameters['code'].endswith('_result=json.dumps(_result)\n')
                return {'structuredContent': {'return_value': json.dumps(payload)}}
        check = object.__new__(probe.BlueprintCheck)
        check.client = OfflineClient()
        marker = "_result={'source':s.editor.document.to_data(),'profile':s.portal_profile.identity}"
        decoded = probe.BlueprintCheck.run(check, prepare_readback_code(marker))
        assert decoded == payload and decoded['source'] == data
        assert not has_transport_placeholder(decoded)
        fixtures.append({'family': family, 'complete_document_equal': True, 'transport_placeholders': False,
                         'json_bytes': len(json.dumps(payload).encode('ascii'))})
receipt = {'action': args.action, 'source_contract_sha256': amendment['source_contract_sha256'],
           'loaded_host_sources': loaded, 'load_result_json_transport': True,
           'prior_attempt_restored': True, 'prior_attempt_capture_count': 0,
           'product_or_clone_resources_changed': False, 'unfrozen_live_root_tools_imported': False,
           'rpc_calls_at_import': 0, 'wgc_calls_at_import': 0, 'offline_fixtures': fixtures, 'qualification': False}
path = CONTROL / ('json-readback-' + args.action + '-import.json')
assert not path.exists()
path.write_text(json.dumps(receipt, indent=2) + '\n', encoding='ascii', newline='\n')
print(json.dumps({'offline_import_passed': True, 'host_source_count': len(loaded),
                  'json_readback_amendment': True, 'action': args.action}), flush=True)
if args.action == 'capture':
    assert (CONTROL / 'json-readback-validate-import.json').exists() and not OUTPUT.exists()
    ready = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    probe.run(argparse.Namespace(project=PROJECT, session=ready['session_file'], owner=ready['owner'], output=OUTPUT))
