"""Preserve raw omissions and fixed root-candidate screening without promotion."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = (ROOT.parent if ROOT.parent.name == '.runtime' else ROOT/'.runtime')/'snow-root-rejected-candidate-r8'
PLANTS = {'crimson_roots', 'warped_roots', 'nether_sprouts'}
LIMITS = {'native_recall': .75, 'native_precision': .75,
          'native_edge_tolerance_pixels': 3}


def record(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def load(path):
    return json.loads(Path(path).read_bytes())


def checked(item):
    actual = record(item['path'])
    if actual['sha256'] != item['sha256']:
        raise ValueError('Original screening evidence changed: '+item['path'])
    return actual


def partition(matrix_path, audit_path, views):
    matrix, audit = load(matrix_path), load(audit_path)
    if (matrix['profile'] != 'static_root_screen' or set(matrix['plants']) != PLANTS or
            matrix['profile_case']['native_target'] != [-47, 117, -70] or
            any(value != [0] for value in matrix['profile_case']['heights'].values()) or
            matrix['limits'] != LIMITS or matrix['source_errors'] or
            not all(matrix[key] for key in ('completed', 'restored', 'source_assets_stable'))):
        raise ValueError('Fixed completed root-screen contract failed')
    if not audit['integrity_passed'] or audit['errors'] or checked(audit['matrix']) != record(matrix_path):
        raise ValueError('Independent audit failed or refers to another matrix')
    expected = {(plant, view) for plant in PLANTS for view in views}
    reports, rows, replays = [], [], []
    for case in matrix['rows']:
        checked(case)
        combination = (case['plant'], case['view'])
        if combination not in expected:
            raise ValueError('Unexpected or duplicate screening case')
        expected.remove(combination)
        report = load(case['path'])
        if (report['native_target'] != [-47, 117, -70] or report['heights'] != [0] or
                report['limits'] != LIMITS or report['cleanup_errors'] or report['binding_read_failures'] or
                not all(report[key] for key in ('completed', 'restored', 'source_assets_stable'))):
            raise ValueError('Original report scope or cleanup failed')
        reports.append(dict(record(case['path']), plant=case['plant'], view=case['view'],
                            completed=True, restored=True, passed=report['passed']))
        for row in report['rows']:
            if row['kind'] == 'blank':
                continue
            rows.append({'plant': case['plant'], 'view': case['view'], 'kind': row['kind'],
                         'height': row['height'], 'world': row['comparisons'],
                         'editor_controls': row.get('editor_controls'),
                         'native_roi_boundary': row.get('native_roi_boundary')})
        replay_path = Path(case['path']).with_name(Path(case['path']).stem+'-replay.json')
        replay = load(replay_path)
        if replay['passed'] != report['passed']:
            raise ValueError('Independent PNG replay changed the failed verdict')
        replays.append(dict(record(replay_path), passed=replay['passed'],
                            original_failed_verdict_preserved=True))
    if expected:
        raise ValueError('Incomplete fixed screening matrix')
    return {'matrix': record(matrix_path), 'audit': record(audit_path),
            'passed': matrix['passed'], 'completed': True, 'restored': True,
            'source_assets_stable': True, 'frozen_source': checked(matrix['frozen_source']),
            'calibration': checked(matrix['calibration']), 'environment': {
                'owner': matrix['owner'], 'game_pid': matrix['game_pid'],
                'session_file': matrix['session_file']},
            'reports': reports, 'rows': rows, 'independent_png_replays': replays,
            'unique_native_pngs': audit['unique_native_pngs_audited'],
            'frozen_files': audit['frozen_source_files_audited'],
            'inspection_sheets_actually_opened': audit['inspection_sheets'],
            'foreground_changes_are_diagnostics': True,
            'foreground_change_observations': audit['foreground_change_observations'],
            'capture_contract': audit['capture_contract']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('raw_matrix', type=Path)
    parser.add_argument('raw_audit', type=Path)
    parser.add_argument('candidate_matrix', type=Path)
    parser.add_argument('candidate_audit', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    raw = partition(args.raw_matrix, args.raw_audit, ('public',))
    candidate = partition(args.candidate_matrix, args.candidate_audit, ('public', 'right'))
    if raw['passed'] or candidate['passed']:
        parser.error('This preserved-failure manifest cannot promote passing candidates')
    frozen = load(ARCHIVE/'snow-r8-root-candidate-prelaunch-source-hashes.json')
    archived_files = {}
    for path in sorted((ARCHIVE/'candidate-source').rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(ARCHIVE/'candidate-source').as_posix()
        if relative not in frozen['hashes_sha256']:
            continue
        artifact = record(path)
        if artifact['sha256'] != frozen['hashes_sha256'][relative]:
            raise ValueError('Archived failed candidate source changed: '+relative)
        archived_files[relative] = artifact
    for plant in PLANTS:
        for directory in ('behavior_pack/netease_blocks', 'resource_pack/models/netease_block'):
            if directory+'/preview_'+plant+'.json' not in archived_files:
                raise ValueError('Failed candidate render asset was not preserved')
    result = {'schema_version': 1, 'plants': sorted(PLANTS),
              'production_acceptance': False, 'all_eight_snow_heights_accepted': False,
              'raw_omissions': raw, 'centered_cross_hypothesis': candidate,
              'construction': 'Unchanged mushroom/fungus centered cross: Y origin0, height16, pivotY8 and full original UV; no fitted XZ or UV changes',
              'geometry_authority': 'Native texture identities and alpha are facts; native mesh/random-offset contract remains unrecovered',
              'original_gates': LIMITS, 'remaining_height_matrix_started': False,
              'failed_candidate_render_assets_archived': str(ARCHIVE/'candidate-source'),
              'archived_candidate_source_files': archived_files,
              'process_resource_diagnostics': record(ARCHIVE/'root-resource-diagnostics-r8.json'),
              'promotion_policy': 'Failed raw Combine and centered-cross experiments remain failed; unaccepted candidates are removed from production registration'}
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2)+'\n', encoding='utf8')
    print(json.dumps(record(args.output)))


if __name__ == '__main__':
    main()
