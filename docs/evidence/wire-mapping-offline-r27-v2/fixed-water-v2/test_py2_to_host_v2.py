"""Independent host controls read actual Py2-exported observer JSON and mutate it."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
sys.path.insert(0, str(HERE))
from water_resource_mapping_v2 import verify_mapping


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def field(packed, key):
    assert set(packed) == {'dict'}
    return next(pair for pair in packed['dict'] if pair[0] == key)


def main():
    exported, output = [Path(value).resolve() for value in sys.argv[1:3]]
    assert output.is_relative_to(HERE) and not output.exists()
    output.mkdir()
    source_export = json.loads((exported / 'export.json').read_bytes())
    assert source_export['native_component_is_fake'] is True
    assert source_export['exact_observer_sha256'] == sha(BASE / 'fixed-water-v1/water_setter_observer.py')
    assert source_export['control_call_count'] == 15 and source_export['snapshot_count'] == 5
    assert source_export['handle_reused_after_successful_removal'] and source_export['creation_history_count'] == 2
    project = BASE.parents[1] / 'projects/wire-r27-fixed-water-v1'
    controls = []

    def passed(name, **details):
        controls.append(dict(details, name=name, passed=True))

    wet_result = verify_mapping(project, exported / 'wet', 'negative-wet-wire')
    assert wet_result['native_call_count'] == 15 and wet_result['checked_group_snapshots'] == 4
    assert len(wet_result['resource_mappings']) == 2
    passed('nonempty_exact_observer_Py2_JSON_to_Py3_host_positive_with_false_exception_hidden_and_handle_reuse',
           calls=15, group_snapshots=4, resource_count=2)
    dry_result = verify_mapping(project, exported / 'dry', 'flat-interior')
    assert dry_result['native_call_count'] == 0 and not dry_result['resource_mappings']
    passed('empty_actual_Py2_observer_dry_export_is_valid_without_wet_claim')
    try:
        verify_mapping(project, exported / 'dry', 'negative-wet-wire')
    except AssertionError:
        passed('empty_actual_Py2_export_cannot_qualify_wet_scope')
    else:
        raise AssertionError('Empty dry observer export accepted as wet')

    # The old exact frozen host must still reject the same valid non-empty export.
    path = BASE / 'fixed-water-v1/water_resource_mapping_v1.py'
    spec = importlib.util.spec_from_file_location('frozen_mapping_v1_under_control', path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    try:
        old.verify_mapping(project, exported / 'wet', 'negative-wet-wire')
    except AssertionError:
        passed('frozen_v1_still_rejects_real_Py2_nonempty_export_without_being_patched')
    else:
        raise AssertionError('Old frozen mapping defect was not reproduced')

    actual = BASE / 'negative-wet-wire-fixed-water-actual-v7/water-receipts'
    actual_result = verify_mapping(project, actual, 'negative-wet-wire')
    assert actual_result['native_call_count'] == 864 and actual_result['checked_group_snapshots'] == 288
    (output / 'actual-v7-readonly-correlation.json').write_text(json.dumps(actual_result, indent=2) + '\n', encoding='ascii')
    passed('preserved_actual_v7_864_calls_48_snapshots_288_groups_correlate_readonly_without_verdict_change',
           actual_game_receipt_calls=864, checked_group_snapshots=288)

    originals = {path.name: json.loads(path.read_bytes()) for path in (exported / 'wet').glob('*.json')}

    def rejects(name, mutate):
        objects = copy.deepcopy(originals)
        mutate(objects)
        folder = output / name
        folder.mkdir()
        for filename, value in objects.items():
            (folder / filename).write_text(json.dumps(value, indent=2) + '\n', encoding='ascii')
        try:
            verify_mapping(project, folder, 'negative-wet-wire')
        except (AssertionError, KeyError, ValueError, TypeError, IndexError, StopIteration) as error:
            passed(name, rejection_type=type(error).__name__)
        else:
            raise AssertionError('Mutated non-empty Py2 export silently accepted: ' + name)

    def first_snapshot(objects):
        return objects['snapshot-001.json']

    def first_ledger_entry(objects):
        return first_snapshot(objects)['applied_native_success_ledger']['dict'][0][1]

    def active_group(objects):
        return first_snapshot(objects)['renderers'][0]['active'][0]

    rejects('native_sequence_mismatch_rejected', lambda objects:
        objects['calls-0001.json']['calls'][0].update(sequence=777))
    rejects('stored_acknowledgement_sequence_mismatch_rejected', lambda objects:
        field(first_ledger_entry(objects), 'sequence').__setitem__(1, 777))

    def wrong_stored_value(objects):
        value = field(first_ledger_entry(objects), 'value')[1]
        field(value, 'tuple')[1]['list'][0] += 9.
    rejects('stored_uniform_value_mismatch_rejected', wrong_stored_value)
    rejects('active_model_handle_mismatch_rejected', lambda objects:
        active_group(objects).update(model_id='foreign-native-handle'))
    rejects('active_resource_name_mismatch_rejected', lambda objects:
        active_group(objects).update(resource_name='modern_projection_liquid_product_flowing_water_grey_world'))
    rejects('active_group_uniform_mismatch_rejected', lambda objects:
        active_group(objects)['uniforms']['tuple'][0]['tuple'].__setitem__(0, 999.))
    rejects('active_visibility_mismatch_rejected', lambda objects:
        active_group(objects).update(visible=False))

    def wrong_actual_uniform(objects):
        call = next(row for row in objects['calls-0001.json']['calls'] if row['method'] == 'SetExtraUniformValue')
        call['args']['tuple'][2]['tuple'][0] += 11.
    rejects('actual_native_uniform_argument_mismatch_rejected', wrong_actual_uniform)

    def single_encoded_value(objects):
        slot = field(first_ledger_entry(objects), 'value')
        floats = field(slot[1], 'tuple')[1]['list']
        slot[1] = {'tuple': floats}
    rejects('incorrect_single_layer_stored_value_encoding_rejected', single_encoded_value)
    rejects('opaque_stored_uniform_encoding_rejected', lambda objects:
        field(first_ledger_entry(objects), 'value').__setitem__(1, {'dict': [['opaque_type', 'unknown']]}))
    rejects('missing_native_call_export_rejected', lambda objects:
        objects['calls-0001.json']['calls'].pop(0))

    def false_return_ledger_forgery(objects):
        call = next(row for row in objects['calls-0001.json']['calls']
                    if row['method'] == 'SetExtraUniformValue' and row.get('result') is False)
        call['result'] = True
    rejects('false_native_return_forged_into_success_rejected', false_return_ledger_forgery)

    def native_exception_forgery(objects):
        call = next(row for row in objects['calls-0001.json']['calls'] if 'exception' in row)
        call.update(completed=True, result=True)
    rejects('native_exception_forged_into_success_rejected', native_exception_forgery)

    report = {'schema': 'wire-r27-offline-v2-real-Py2-observer-to-Py3-host-nonempty-controls',
              'passed': True, 'controls': controls, 'control_count': len(controls),
              'exact_frozen_observer_sha256': source_export['exact_observer_sha256'],
              'original_frozen_v1_mapping_sha256': sha(path),
              'v2_candidate_sha256': sha(HERE / 'water_resource_mapping_v2.py'),
              'Py2_export_manifest_sha256': sha(exported / 'export.json'),
              'fake_native_components_in_Py2_controls': True,
              'actual_v7_evidence_read_only': True, 'MC_started': False, 'runtime_calls': 0,
              'original_wet_report_restored': False, 'original_reports_or_freeze_modified': False,
              'production_changed': False, 'candidate_promoted': False, 'manual_closures': 0}
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'passed': True, 'controls': len(controls), 'MC_started': False,
                      'report_sha256': sha(output / 'report.json')}))


if __name__ == '__main__':
    main()
