"""Preserve an interrupted opaque-witness experiment without scoring partial epochs."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from analyze_liquid_workspace import capture_failures
from liquid_coordinate_markers import fingerprint, manifest, write
from liquid_static_coordinate_epochs import check


def read(path):
    return json.loads(Path(path).read_bytes())


def checked_ref(ref):
    actual = fingerprint(ref['path'])
    if actual['sha256'] != ref['sha256']:
        raise ValueError('Evidence bytes changed: ' + ref['path'])
    return actual


def configurations(old_plan_path, receipt):
    expected = {**{name: False for name in ('auto_hot_reload_mods', 'auto_hot_reload_ui',
                                          'auto_hot_reload_shaders', 'auto_hot_reload_materials')},
                'world_type': 2, 'world_seed': 0, 'game_mode': 1}
    receipts = [read(old_plan_path.parent / epoch / 'session-receipt.json')
                for epoch in read(old_plan_path)['epochs']] + [receipt]
    result = []
    for row in receipts:
        path = Path(row['session_file']).parent / '.mcdev.json'
        config = read(path)
        selected = {key: config.get(key) for key in expected}
        result.append({'id': row['id'], 'owner': row['owner'], 'generated_configuration': fingerprint(path),
                       'observed': selected, 'matches_declared_controls': selected == expected})
    return {'expected': expected, 'sessions': result,
            'all_generated_configurations_match': all(row['matches_declared_controls'] for row in result),
            'scope': 'Generated managed configs only. Configuration equality does not identify the binding failure cause.'}


def package(plan_path, native_path, output):
    if output.exists():
        raise ValueError('Choose a fresh interrupted-experiment evidence output')
    plan, native = read(plan_path), read(native_path)
    check(plan)
    plan_ref = fingerprint(plan_path)
    if native['static_coordinate_plan'] != plan_ref or native['static_epoch'] != 'low':
        raise ValueError('Interrupted report does not reference this exact LOW plan')
    if native['completed'] or native['restored'] or not native['cleanup_errors']:
        raise ValueError('This record requires the original interrupted, unrestored native result')
    if native['opaque_cube_alias'] != plan['cube_alias_override']:
        raise ValueError('Opaque witness alias differs from the frozen experiment')
    epoch = plan_path.parent / 'low'
    receipt = read(epoch / 'session-receipt.json')
    session = read(receipt['session_file'])
    force = read(epoch / 'stop-force-result.json')
    if session['owner'] != receipt['owner'] or session['state'] != 'stopped' or session['ready']:
        raise ValueError('Owned interrupted session is not stopped')
    if (force['session_id'] != receipt['id'] or force['returncode'] != 0
            or any(value is not None for value in force['after'].values())):
        raise ValueError('Independent exact-identity stop verification failed')
    sys.path.insert(0, str(Path(plan['project']) / '.agents/skills/pyreact-debugging/scripts'))
    from _session import process_identity
    if any(process_identity(receipt[kind + '_pid']) == receipt[kind + '_identity']
           for kind in ('game', 'mcdk')):
        raise ValueError('An owned interrupted process is still present')
    restored = read(epoch / 'restored.json')
    cube_restored = read(epoch / 'cube-restored.json')
    if (not restored['original_absence_restored'] or not restored['full_resource_manifest_equals_baseline']
            or not cube_restored['original_blocks_bytes_restored']
            or not cube_restored['full_resource_manifest_equals_baseline']
            or manifest(Path(plan['project'])) != plan['baseline_resource_manifest']):
        raise ValueError('Local resource bytes were not restored to the exact baseline')
    calibration_ref = checked_ref(native['calibration'])
    calibration = read(calibration_ref['path'])
    if (not all(calibration.get(key) for key in ('completed', 'passed', 'restored'))
            or calibration['cleanup_errors'] or calibration['session_file'] != receipt['session_file']):
        raise ValueError('Independent same-session camera calibration did not pass and restore')
    captures, cases = {}, []
    for row in native['cases']:
        cases.append({'case': row['case'], 'completed': row['completed'],
                      'native_controls_passed': row.get('native_controls_passed'),
                      'controls': {name: {'completed': item['completed'],
                                         'native_gate_summary': {key: item.get('native_gate', {}).get(key)
                                             for key in ('public_snapshot_unchanged', 'failure_reasons',
                                                         'native_layer_conversion_required', 'flow_disabled',
                                                         'geometry_accepted')}}
                                   for name, item in row['controls'].items()}})
        for name, item in row['controls'].items():
            record = item.get('capture')
            if record:
                checked_ref(record)
                captures[row['case'] + '/' + name] = record['capture']
    provenance_failures = capture_failures(captures, native['session_binding'])
    pngs = [{'label': label, 'file': checked_ref(record),
             'frame': record['frame'], 'background_only': record['background_only'],
             'foreground_unchanged': record['foreground_unchanged']}
            for label, record in captures.items()]
    lifecycle_names = ('session-receipt.json', 'installed.json', 'cube-installed.json',
        'restored.json', 'cube-restored.json', 'capture-stdout.txt', 'capture-stderr.txt',
        'stop-attempt1-stdout.txt', 'stop-attempt1-stderr.txt', 'stop-force-stdout.txt',
        'stop-force-stderr.txt', 'stop-force-result.json')
    old_start = plan['prior_startup_only']
    for key in ('receipt', 'stopped_session'):
        checked_ref(old_start[key])
    result = {'schema': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'Interrupted LOW epoch of the same-alias opaque-cube experiment; no four-epoch fit',
        'frozen_plan': plan_ref, 'previous_water_plan': checked_ref(plan['previous_static_plan']),
        'native_report': fingerprint(native_path), 'calibration': calibration_ref,
        'session': {key: receipt[key] for key in ('id', 'owner', 'game_pid', 'game_identity',
                                                 'mcdk_pid', 'mcdk_identity')},
        'stopped_session': fingerprint(receipt['session_file']),
        'lifecycle': {name: fingerprint(epoch / name) for name in lifecycle_names},
        'original_native_result': {'completed': native['completed'], 'restored': native['restored'],
            'error': native.get('error'), 'cleanup_errors': native['cleanup_errors'], 'cases': cases},
        'available_native_pngs': pngs, 'available_native_png_count': len(pngs),
        'available_capture_provenance_failures': provenance_failures,
        'available_capture_provenance_passed': not provenance_failures,
        'local_resource_restoration': {'flow': restored, 'cube': cube_restored},
        'exact_owned_identities_absent': True, 'force_stop': force,
        'configuration_comparison': configurations(Path(plan['previous_static_plan']['path']), receipt),
        'startup_only_previous_route': old_start,
        'geometry': {'cube_surfaces': plan['cube_surfaces'], 'water_grid': plan['sample_grid'],
            'cube_grid': plan['cube_sample_grid'], 'source_neighbor_context_changed': False,
            'water_scope': plan['water_scope'], 'cube_scope': plan['cube_scope']},
        'missing_epochs': [epoch for epoch in plan['epochs'] if epoch != 'low'],
        'missing_or_incomplete_cases': [row['case'] for row in plan['geometry_sequences']
            if not any(case['case'] == row['case'] and case['completed'] for case in native['cases'])],
        'configuration': {'originally_absent': plan['original_configuration_absent'],
            'temporary_config': plan['configuration'], 'restoration_pending': True},
        'cube_sampling_accepted': False, 'native_uv_accepted': False, 'native_animation_accepted': False,
        'production_accepted': False, 'production_profile_enabled': False,
        'limits': 'Eight fresh LOW PNGs and a passed camera calibration do not provide LOW/HIGH transfer, coordinate/complement observations, or a completed/restored native experiment. No cube fit or water accuracy is inferred.'}
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'native', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = package(args.plan.resolve(), args.native.resolve(), args.output.resolve())
    print(json.dumps({key: result[key] for key in ('available_native_png_count',
        'available_capture_provenance_passed', 'exact_owned_identities_absent', 'native_uv_accepted',
        'production_accepted')}))
