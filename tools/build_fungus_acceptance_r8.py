"""Join unchanged R7 boundary and R8 remaining-height fungus evidence."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLANTS = ('crimson_fungus', 'warped_fungus')
VIEWS = {'public': [-2., .15, -2.5], 'right': [2., .15, -2.5]}
BOUNDARY = {'crimson_fungus': [4, 5], 'warped_fungus': [3, 4]}
REMAINING = {'crimson_fungus': [0, 1, 2, 3, 6, 7],
             'warped_fungus': [0, 1, 2, 5, 6, 7]}
LIMITS = {'native_recall': .75, 'native_precision': .75,
          'native_edge_tolerance_pixels': 3}


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def checked_reference(reference):
    actual = record(reference['path'])
    if actual['sha256'] != reference['sha256']:
        raise ValueError('Evidence changed: '+reference['path'])
    return actual


def load(path):
    return json.loads(Path(path).read_bytes())


def build(boundary_path, matrix_path, audit_path):
    old, matrix, audit = (load(path) for path in (boundary_path, matrix_path, audit_path))
    if old['accepted_scope']['snow_heights'] != BOUNDARY:
        raise ValueError('R7 boundary partition changed')
    if matrix['profile'] != 'fungus_remaining' or matrix['profile_case']['heights'] != REMAINING:
        raise ValueError('R8 remaining-height partition changed')
    if matrix['profile_case']['views'] != VIEWS or matrix['limits'] != LIMITS:
        raise ValueError('Fixed views or original pixel gates changed')
    if matrix['profile_case']['native_target'] != [-47, 117, -70]:
        raise ValueError('Native reference cell changed')
    if not all(matrix[key] for key in ('completed', 'restored', 'passed', 'source_assets_stable')):
        raise ValueError('R8 capture is incomplete, unrestored or failed')
    if matrix['source_errors'] or not audit['integrity_passed'] or audit['errors']:
        raise ValueError('R8 source or capture integrity failed')
    if checked_reference(audit['matrix']) != record(matrix_path):
        raise ValueError('Audit refers to a different matrix')
    switches = audit['foreground_change_observations']
    if len(switches) != 18 or not all(row['background_safe'] and row['reliable'] for row in switches):
        raise ValueError('Original ordinary other-application switching observations changed')
    assets = old['capture_and_source_audit']['production_render_asset_sha256']
    for relative, expected in assets.items():
        if record(ROOT/relative)['sha256'] != expected:
            raise ValueError('R7 accepted fungus render asset changed: '+relative)
    original_artifacts = [checked_reference(item) for item in old['artifacts']]
    summaries, measurements, replays = [], [], []
    combinations = {(plant, view) for plant in PLANTS for view in VIEWS}
    for case in matrix['rows']:
        checked_reference(case)
        report = load(case['path'])
        combination = (case['plant'], case['view'])
        if combination not in combinations:
            raise ValueError('Duplicate or unexpected R8 plant/view combination')
        combinations.remove(combination)
        if (report['heights'] != REMAINING[case['plant']] or report['limits'] != LIMITS or
                report['world_camera_offset'] != VIEWS[case['view']] or
                report['native_target'] != [-47, 117, -70] or
                report['cleanup_errors'] or report['binding_read_failures']):
            raise ValueError('R8 report fixed parameters or cleanup changed')
        if not all(report[key] for key in ('completed', 'restored', 'passed', 'source_assets_stable')):
            raise ValueError('R8 report failed')
        summaries.append(dict(record(case['path']), plant=case['plant'], view=case['view'],
                              heights=report['heights'], scopes=report['scopes'],
                              nonblank_rows=report['independent_nonblank_capture_rows'],
                              covered_editor_cases=report['covered_cases_captured']))
        for row in report['rows']:
            if row['kind'] == 'blank':
                continue
            measurements.append({'plant': case['plant'], 'view': case['view'],
                                 'kind': row['kind'], 'height': row['height'],
                                 'world': row['comparisons'],
                                 'editor_controls': row.get('editor_controls'),
                                 'native_roi_boundary': row.get('native_roi_boundary')})
        replay_path = Path(case['path']).with_name(Path(case['path']).stem+'-replay.json')
        if not load(replay_path)['passed']:
            raise ValueError('Independent original PNG replay failed')
        replays.append(dict(record(replay_path), passed=True))
    if combinations:
        raise ValueError('R8 plant/view combination is missing')
    return {
        'schema_version': 1,
        'accepted_scope': {
            'plants': list(PLANTS), 'snow_heights': {plant: list(range(8)) for plant in PLANTS},
            'dry_native_controls': True, 'world_modes': ['full', 'missing'],
            'independent_editor_controls': True, 'views': VIEWS,
            'native_target': [-47, 117, -70], 'all_eight_snow_heights_accepted': True,
            'all_current_plants_accepted': False,
            'other_positions_or_runtime_versions_accepted': False},
        'geometry': dict(deepcopy(old['geometry']),
                         scope='Dry and all eight snow heights at the two fixed views and measured cell; native mesh and random-offset contract remain unrecovered'),
        'environment': {'nemc_version': old['environment']['nemc_version'],
                        'runtime_minecraft_version': old['environment']['runtime_minecraft_version'],
                        'r7': old['environment'], 'r8_owner': matrix['owner'],
                        'r8_session_file': matrix['session_file'], 'r8_game_pid': matrix['game_pid'],
                        'r8_instance_state': 'stopped', 'r8_game_alive': False, 'r8_mcdk_alive': False,
                        'r8_stop_condition': 'Normal owned WM_CLOSE; both processes exited; no force'},
        'protected_startup': {'r7': old['protected_startup'],
                              'r8': {'guard_dll': old['protected_startup']['guard_dll'],
                                     'guard_sha256': old['protected_startup']['guard_sha256'],
                                     'isolated_mcdk_sha256': old['protected_startup']['isolated_mcdk_sha256'],
                                     'loaded_guard_module_verified': True,
                                     'desktop_input_resize_activation_used': False,
                                     'guard_bypasses': 0,
                                     'owner': matrix['owner'], 'game_pid': matrix['game_pid']}},
        'original_gates': old['original_gates'],
        'public_parameters': dict(deepcopy(old['public_parameters']),
                                  heights={plant: list(range(8)) for plant in PLANTS},
                                  r8_profile_field='fungus_remaining', native_target=[-47, 117, -70]),
        'evidence_partitions': {
            'r7_boundary': {'acceptance_manifest': record(boundary_path), 'snow_heights': BOUNDARY,
                            'matrix': old['matrix'], 'audit': old['capture_and_source_audit'],
                            'artifacts': original_artifacts, 'rows': old['rows']},
            'r8_remaining': {'matrix': record(matrix_path), 'audit': record(audit_path),
                             'calibration': checked_reference(matrix['calibration']),
                             'frozen_source': checked_reference(matrix['frozen_source']),
                             'snow_heights': REMAINING, 'reports': summaries,
                             'rows': measurements, 'offline_png_replays': replays,
                             'unique_native_pngs': audit['unique_native_pngs_audited'],
                             'frozen_files': audit['frozen_source_files_audited'],
                             'inspection_sheets_actually_opened': audit['inspection_sheets'],
                             'foreground_changes_are_diagnostics': True,
                             'capture_contract': audit['capture_contract'],
                             'ordinary_other_application_switch_count': len(switches),
                             'ordinary_other_application_switch_observations': switches}},
        'production_render_asset_sha256': assets,
        'preserved_failures': old['preserved_failures'],
        'promotion': 'Union of disjoint original height partitions after independent frozen capture, PNG audit and replay; historical reports remain unchanged',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('matrix', type=Path)
    parser.add_argument('audit', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    result = build(ROOT/'docs/snow-fungus-boundary-acceptance-r7.json', args.matrix, args.audit)
    text = json.dumps(result, ensure_ascii=True, indent=2)+'\n'
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding='utf8') != text:
            parser.error('Generated acceptance manifest differs')
    else:
        args.output.write_text(text, encoding='utf8')
    print(json.dumps(record(args.output)))


if __name__ == '__main__':
    main()
