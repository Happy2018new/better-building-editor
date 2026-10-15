"""Record chest editor holdouts without reclassifying historical failures."""
import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path

from pack_entity_visual_evidence_r8 import frame_controls
from verify_hanging_sign_front_holdout import record_file

ROOT = Path(__file__).resolve().parents[1]
LIMITS = {'minimum_native_pixels': 1000, 'shape_iou': .82, 'texture_cosine': .45,
          'scale_relative_error': .2, 'center_distance_pixels': 3, 'boundary_rms_pixels': 4}


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def pack_run(directory, registry):
    report = load(directory / 'report.json')
    frozen = load(directory / 'frozen_source.json')
    after = load(directory / 'frozen_source_after.json')
    assert frozen['limits'] == LIMITS
    source = next(row for row in frozen['production']
                  if Path(row['path']).name == 'block_registry_data.py')
    assert source['sha256'] == registry['sha256']
    frames = list(frame_controls(report))
    reliable = bool(frames) and all(
        row['capture'].get('reliable') and row['capture'].get('background_safe') and
        row['capture'].get('native_resolution') and record_file(Path(row['path']))['sha256'] == row['sha256']
        for row in frames)
    editor = [row for row in frames if 'editor_before' in row]
    stable = bool(editor) and all(row['editor_before'] == row['editor_after'] and
                                 row['editor_before']['document'] == row['source']['document']
                                 for row in editor)
    cases = []
    for case in report['cases']:
        metadata = case['public_source']['native_client_document']['registry']
        assert metadata == {'version': registry['version'], 'sha256': registry['palette_sha256']}
        comparison = case['comparison']
        passed = (case['native_signal']['pixels'] >= 1000 and comparison['shape_iou'] >= .82 and
                  comparison['texture_cosine'] is not None and comparison['texture_cosine'] >= .45 and
                  comparison['scale_relative_error'] <= .2 and
                  comparison['alignment']['center_distance_pixels'] <= 3 and
                  comparison['alignment']['boundary_rms_pixels'] <= 4)
        cases.append({key: case[key] for key in ('id', 'name', 'direction', 'paired', 'fixture', 'cells')} |
                     {'passed_original_gates': passed, 'comparison': comparison,
                      'native_pixels': case['native_signal']['pixels'],
                      'public_source_unchanged': case['public_source']['public_source_unchanged']})
    accepted = (report['completed'] and report['passed'] and report['restored'] and
                not report.get('cleanup_errors') and after['production_and_tools_unchanged'] and
                reliable and stable and bool(cases) and
                all(row['passed_original_gates'] and row['public_source_unchanged'] for row in cases))
    return {'name': directory.name, 'accepted': bool(accepted),
            'completed': report['completed'], 'passed': report['passed'], 'restored': report['restored'],
            'error': report.get('error'), 'scope': report['scope'], 'limits': LIMITS,
            'frame_count': len(frames), 'all_frames_reliable_background_wgc': reliable,
            'editor_document_and_camera_preserved': stable,
            'production_and_tools_unchanged': after['production_and_tools_unchanged'],
            'registration': report.get('registration'), 'native_background': report.get('native_background'),
            'cases': cases, 'frozen_registry_source': source,
            'artifacts': [record_file(path) for path in sorted(directory.iterdir()) if path.is_file()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', type=Path, required=True)
    args = parser.parse_args()
    generated = ROOT / 'behavior_pack/modern_projection/projection/block_registry_data.py'
    embedded = {}
    for node in ast.parse(generated.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('SOURCE_VERSION', 'SOURCE_SHA256'):
                embedded[node.targets[0].id] = ast.literal_eval(node.value)
    manifest = load(ROOT / 'tools/data/block_registry_manifest.json')
    palette = record_file(ROOT / manifest['source_file'])
    assert palette['sha256'].lower() == manifest['source_sha256'].lower() == embedded['SOURCE_SHA256'].lower()
    assert manifest['game_version'] == embedded['SOURCE_VERSION']
    registry = dict(record_file(generated), version=embedded['SOURCE_VERSION'], palette_sha256=palette['sha256'].lower())
    runs = [pack_run(args.artifacts / name, registry) for name in
            ('chest-editor-r9-public-v1', 'chest-editor-r9-public-v2', 'chest-editor-r9-public-v3')]
    assert [row['accepted'] for row in runs] == [False, False, True]
    index_path = ROOT / 'tools/data/entities_visual_viewed_frames_r9.json'
    viewed = load(index_path)
    reviewed = [record_file(args.artifacts / run / name)
                for run, names in viewed['runs'].items() for name in names]
    session = load(args.session)
    assert session['id'] == args.artifacts.parent.name and session['owner'] == 'p0-entities-r9'
    assert session['state'] == 'stopped'
    cleanup_path = args.artifacts / 'entities-r9-chest-editor-v3-cleanup.json'
    cleanup = load(cleanup_path)
    assert cleanup['completed'] and cleanup['restored'] and cleanup['read_only']
    result = {'schema': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
              'pack_tool': record_file(Path(__file__)), 'game_version': registry['version'],
              'palette_sha256': registry['palette_sha256'], 'palette_dump': palette,
              'registry_manifest': record_file(ROOT / 'tools/data/block_registry_manifest.json'),
              'registry_source': registry, 'production_rendering_changed': False,
              'scope': 'Actual ordinary editor Scene viewport versus native world chest, three public source cases, top view only',
              'native_background_context': 'Predeclared quartz plane replaces public fixture supports; identical in native shown and empty controls',
              'registration_contract': 'Independent stone cube fixes uniform scale and centers before any chest capture; chest pixels never recalibrate',
              'accepted_runs': ['chest-editor-r9-public-v3'], 'original_gates': LIMITS,
              'historical_evidence': {'reclassified': False, 'prior_r8_manifest': record_file(ROOT / 'tools/data/entities_visual_acceptance_r8.json'),
                                      'prior_r8_viewed_index': record_file(ROOT / 'tools/data/entities_visual_viewed_frames_r8.json'),
                                      'chest_candidate_008ca89_merged': False},
              'visual_review': {'observer': viewed['observer'], 'index': record_file(index_path),
                                'frames_actually_opened': reviewed},
              'runtime_cleanup': {'cleanup_audit': record_file(cleanup_path),
                                  'recorded_grounded_baseline': record_file(args.artifacts / 'entities-r9-recorded-grounded-baseline.json'),
                                  'preserved_failed_guessed_baseline': record_file(args.artifacts / 'entities-r9-grounded-baseline.json'),
                                  'stopped_session': record_file(args.session), 'grounded_foot': [.5, 74., .5],
                                  'no_corrective_audit_teleport': True,
                                  'quiet_handle_growth': {'interval_seconds': 30, 'before': 189142, 'after': 192497, 'instance_recycled': True}},
              'pending_scopes': ['Real partial-double-chest occupied lifecycle', 'Other chest materials, directions and non-top views',
                                 'Head, frame and banner visible content boundaries'], 'runs': runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'accepted_runs': 1, 'preserved_runs': len(runs), 'viewed_frames': len(reviewed)}))


if __name__ == '__main__':
    main()
