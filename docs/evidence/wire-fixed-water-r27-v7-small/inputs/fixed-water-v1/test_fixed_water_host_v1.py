"""Offline exact-source controls; fake transport, no game/process capability claim."""
import ast
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
import fixed_water_receipts_v1 as host
from water_resource_mapping_v1 import verify_mapping


def load(name):
    return ast.parse((BASE / name).read_text(encoding='utf8'))


def function(tree, name):
    return next(node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name == name)


def main():
    out = Path(sys.argv[1]).resolve()
    assert out.is_relative_to(HERE) and not out.exists()
    out.mkdir()
    controls = []
    before, after = load('trial_capture_v6.py'), load('trial_capture_v7_fixed_water.py')
    assert ast.dump(function(before, 'wire_metric')) == ast.dump(function(after, 'wire_metric'))
    controls.append({'name': 'entire_original_strict_wire_metric_AST_is_identical', 'passed': True})
    expected = {'observer_client_v3.py': 'a23060f6eb67f080f28bdae32adab101f33a87467e287bd817ed161d12574729',
                'trial_payloads_v3.py': 'f84a3e7ecc6dd080f6322de03617ada2a2364ea5d7d70960c6ba340a5a97c115',
                'candidate-drop-direct-only/render_context.py': 'cd37869a6d9f1222e148e9fc7143fc51f98648e75cd31523eddaed02db76fa1a',
                'phase_transport_v5.py': '2a284678019ad5c78748d23c3adb9ca8e53b4777155d56946ec57663d6c45c9e'}
    assert all(hashlib.sha256((BASE / path).read_bytes()).hexdigest() == digest for path, digest in expected.items())
    controls.append({'name': 'original_native_payload_observer_candidate_game_CRC32_bytes_remain_pinned', 'passed': True})
    for path in ('water_setter_observer.py', 'fixed_water_receipts_v1.py', 'water_resource_mapping_v1.py'):
        ast.parse((HERE / path).read_text(encoding='utf8'))
    for path in ('trial_capture_v7_fixed_water.py', 'cold_lifecycle_v8_fixed_water.py'):
        load(path)
    controls.append({'name': 'all_five_new_host_observer_mapping_sources_parse', 'passed': True})
    read_code = ast.dump(function(after, 'run'))
    assert 'water_retirement' in read_code and 'water_mapping' in read_code
    controls.append({'name': 'water_retirement_and_resource_mapping_are_explicit_cleanup_steps', 'passed': True})

    class FakeCheck:
        def __init__(self, fail_reads=False):
            self.retired = False
            self.fail_reads = fail_reads

        def run(self, code):
            if 'observer.install()' in code:
                return {'installed': True, 'calls': 0, 'renderers': 0}
            if 'read_calls(' in code:
                if self.fail_reads:
                    raise RuntimeError('intentional-private-transport-read-failure')
                return {'schema': 'wire-r27-water-native-calls-v1', 'after': 0, 'through': 0,
                        'total': 0, 'calls': []}
            if 'observer.retire(' in code:
                self.retired = True
                return {'marker_removed': True, 'restored': True, 'complete': True,
                        'all_call_receipts_exported': True, 'record_count': 0,
                        'alive': {'dict': []}, 'budget_exceeded': False, 'errors': []}
            raise AssertionError('Unexpected fake transport payload')

    check = FakeCheck()
    sink = host.WaterReceiptSink(out / 'empty', HERE / 'water_setter_observer.py')
    sink.install(check)
    result = sink.retire(check)
    assert check.retired and result['passed'] and sink.after == 0
    controls.append({'name': 'zero_call_dry_fixture_still_installs_retires_and_exports_census', 'passed': True})
    bad = FakeCheck(fail_reads=True)
    sink = host.WaterReceiptSink(out / 'failed-read', HERE / 'water_setter_observer.py')
    sink.install(bad)
    result = sink.retire(bad)
    assert bad.retired and not result['passed'] and result['retirement']['restored']
    assert result['errors'][0]['step'] == 'flush'
    controls.append({'name': 'failed_export_still_executes_actual_restore_request_and_keeps_failure', 'passed': True})
    # Empty actual-call receipts are a valid dry sentinel but must never qualify wet water.
    # The resource project is read-only here. No fixed clock assertion is reached for zero calls.
    project = BASE.parents[1] / 'projects/wire-r27-crc32-mutex-v10'
    dry = verify_mapping(project, out / 'empty', 'flat-interior')
    assert dry['passed'] and dry['resource_mappings'] == []
    try:
        verify_mapping(project, out / 'empty', 'negative-wet-wire')
    except AssertionError:
        pass
    else:
        raise AssertionError('Empty water receipt silently qualified a wet fixture')
    controls.append({'name': 'wet_scope_rejects_absent_actual_FreeModel_and_active_group_receipts', 'passed': True})
    report = {'schema': 'wire-r27-private-fixed-water-host-controls-v1', 'passed': True,
              'controls': controls, 'control_count': len(controls), 'runtime_calls': 0,
              'MC_started': False, 'fake_transport_only': True, 'actual_game_capability_proven': False,
              'production_changed': False, 'candidate_promoted': False, 'manual_closures': 0}
    (out / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': True, 'control_count': len(controls), 'runtime_calls': 0}))


if __name__ == '__main__':
    main()
