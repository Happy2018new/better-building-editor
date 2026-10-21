"""Read-only exact-call decoding analysis; never rewrites frozen inputs or verdicts."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'fixed-water-v1'))
from water_resource_mapping_v1 import unpack


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    output = HERE / 'fixed-water-v7-readonly-ledger-analysis.json'
    assert not output.exists()
    folder = HERE / 'negative-wet-wire-fixed-water-actual-v7'
    receipt_folder = folder / 'water-receipts'
    project = HERE.parents[1] / 'projects/wire-r27-fixed-water-v1'
    report = json.loads((folder / 'report.json').read_bytes())
    assert report['completed'] and not report['restored']
    assert report['cleanup_errors'] == [{'step': 'water_observer', 'error': 'AssertionError: '}]
    assert report['independent_audit']['restored'] and report['runtime_and_host_unchanged']
    calls = []
    files = [{'path': path.relative_to(HERE).as_posix(), 'sha256': sha(path)} for path in
             sorted(receipt_folder.glob('*.json'))]
    for path in sorted(receipt_folder.glob('calls-*.json')):
        packet = json.loads(path.read_bytes())
        assert packet['after'] == len(calls)
        calls.extend(packet['calls'])
        assert packet['through'] == len(calls)
    assert len(calls) == 864
    assert [call['sequence'] for call in calls] == list(range(1, len(calls) + 1))
    assert all(call['native_called'] and call['completed'] and call['result'] for call in calls)
    retirement = json.loads((receipt_folder / 'retirement.json').read_bytes())
    assert retirement['complete'] and retirement['restored'] and retirement['marker_removed']
    assert retirement['record_count'] == retirement['exported_count'] == len(calls)
    assert not retirement['alive']['dict'] and not retirement['errors'] and not retirement['budget_exceeded']
    models_path = project / 'resource_pack/models/netease_models.json'
    materials_path = project / 'resource_pack/materials/entity.material'
    models = json.loads(models_path.read_bytes())
    materials = json.loads(materials_path.read_bytes())['materials']
    expected = json.loads((HERE / 'fixed-water-v1/shader-change-manifest-v1.json').read_bytes())
    shaders = {row['path']: row for row in expected['shaders']}
    mappings, method_counts = {}, {}
    for call in calls:
        method_counts[call['method']] = method_counts.get(call['method'], 0) + 1
        if call['method'] != 'CreateFreeModel':
            continue
        resource = unpack(call['args'])[0]
        model = models[resource]
        candidate = [(name, value) for name, value in materials.items()
                     if name.split(':')[0] == model['material']]
        assert len(candidate) == 1
        material_name, material = candidate[0]
        fragment_path = 'resource_pack/' + material['fragmentShader']
        assert fragment_path in shaders and sha(project / fragment_path) == shaders[fragment_path]['fixed_sha256']
        dependencies = ['resource_pack/models/netease_models.json', 'resource_pack/materials/entity.material',
                        fragment_path, 'resource_pack/' + material['vertexShader'],
                        'resource_pack/models/' + model['mesh'], 'resource_pack/models/' + model['skeleton']]
        dependencies += ['resource_pack/textures/models/' + name + '.png' for name in model['texture'].values()]
        mappings[resource] = {'resource_name': resource, 'model_entry': model,
                              'material_name': material_name, 'material_entry': material,
                              'frozen_dependencies': [{'path': name, 'sha256': sha(project / name)} for name in dependencies]}
    snapshot_rows = []
    checked_groups = mismatching_before_decode = decoded_values = 0
    for path in sorted(receipt_folder.glob('snapshot-*.json')):
        snapshot = json.loads(path.read_bytes())
        alive, ledger = {}, {}
        for call in calls[:snapshot['call_count']]:
            args, rid = unpack(call['args']), call['renderer_id']
            if call['method'] == 'CreateFreeModel':
                alive[(rid, unpack(call['result']))] = args[0]
            elif call['method'] == 'RemoveFreeModel':
                alive.pop((rid, args[0]), None)
            elif call['method'] == 'SetExtraUniformValue':
                ledger[(rid, args[0], args[1])] = {'sequence': call['sequence'], 'value': args[2]}
        assert unpack(snapshot['alive']) == alive
        # Observer writes _pack(args[2]) into applied ledger, then packs the whole
        # ledger for snapshot transport. The inner value remains intentionally
        # packed after one outer unpack; frozen verifier compared that dict to a tuple.
        transported_ledger = unpack(snapshot['applied_native_success_ledger'])
        mismatches = [key for key in ledger if transported_ledger.get(key) != ledger[key]]
        mismatching_before_decode += len(mismatches)
        assert set(transported_ledger) == set(ledger)
        for key, value in transported_ledger.items():
            assert set(value) == {'sequence', 'value'}
            assert value['sequence'] == ledger[key]['sequence']
            value['value'] = unpack(value['value'])
            decoded_values += 1
        assert transported_ledger == ledger, 'Additional stored-value decode did not explain frozen mismatch'
        count = 0
        for renderer in snapshot['renderers']:
            for kind in ('active', 'staging', 'retired'):
                for group in renderer[kind]:
                    rid, handle = renderer['renderer_id'], unpack(group['model_id'])
                    assert alive[(rid, handle)] == group['resource_name']
                    assert group['resource_name'] in mappings
                    uniforms = unpack(group['uniforms'])
                    for index, value in enumerate(uniforms[:3], 1):
                        assert ledger[(rid, handle, index)]['value'] == value
                    assert type(group['visible']) is bool
                    visible_value = uniforms[3] if group['visible'] else uniforms[3][:3] + (0.,)
                    assert ledger[(rid, handle, 4)]['value'] == visible_value
                    count += 1
        checked_groups += count
        snapshot_rows.append({'path': path.name, 'label': snapshot['label'], 'call_count': snapshot['call_count'],
                              'checked_groups': count, 'frozen_one_decode_mismatches': len(mismatches),
                              'additional_stored_value_decode_matches_all_native_acknowledgements': True})
    assert mappings and checked_groups and mismatching_before_decode
    for sample_prefix in ('opaque_top', 'opaque_grazing'):
        samples = [row for row in report['samples'] if row['label'].startswith(sample_prefix + '_')]
        assert [row['mode'] for row in samples] == ['base', 'repeat', 'candidate', 'restored']
        assert all(row['completed'] for row in samples)
        reference = samples[0]['wire']
        assert all(all(row['wire'][key] == reference[key] for key in
                       ('box', 'wire_pixels', 'mask_sha256', 'wire_rgb_sha256')) for row in samples)
    result = {'schema': 'wire-r27-fixed-water-v7-readonly-double-packed-ledger-analysis',
              'passed': True, 'report_path': (folder / 'report.json').relative_to(HERE).as_posix(),
              'original_report_sha256': sha(folder / 'report.json'),
              'original_frozen_host_verdict': {'completed': True, 'restored': False,
                                             'cleanup_errors': report['cleanup_errors']},
              'original_report_or_freeze_rewritten': False, 'runtime_calls': 0, 'MC_started': False,
              'strict_opaque_wire_mask_RGB_all_modes_match': True, 'actual_native_calls': len(calls),
              'method_counts': method_counts, 'all_call_arguments_returns_and_order_retained': True,
              'all_native_calls_succeeded': True, 'water_observer_exact_restoration_and_zero_alive': True,
              'original_independent_state_audit_restored': True, 'runtime_and_host_sources_unchanged': True,
              'mapping_failure_site': 'water_resource_mapping_v1.py:79',
              'mapping_failure_cause': 'Applied ledger value is packed once when storing an acknowledged native uniform and again inside the complete snapshot. Frozen host unpacked only the outer transport before comparing that packed tuple dictionary with a reconstructed native tuple.',
              'additional_stored_value_decodes': decoded_values,
              'frozen_one_decode_inequalities': mismatching_before_decode,
              'all_native_acknowledgements_equal_after_exact_additional_value_decode': True,
              'checked_active_group_snapshots': checked_groups, 'snapshots': snapshot_rows,
              'actual_FreeModel_to_frozen_shader_mappings': list(mappings.values()),
              'source_receipt_files': files, 'independent_native_readback': False,
              'engine_clock_readback': False, 'individual_v6_pixel_causality_proven': False,
              'production_changed': False, 'candidate_promoted': False, 'manual_closures': 0}
    with output.open('x', encoding='ascii') as stream:
        json.dump(result, stream, ensure_ascii=True, indent=2)
        stream.write('\n')
    print(json.dumps({'passed': True, 'calls': len(calls), 'group_snapshots': checked_groups,
                      'frozen_inequalities': mismatching_before_decode, 'decoded_values': decoded_values,
                      'output_sha256': sha(output), 'original_report_changed': False}))


if __name__ == '__main__':
    main()
