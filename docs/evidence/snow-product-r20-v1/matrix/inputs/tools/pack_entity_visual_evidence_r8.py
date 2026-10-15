"""Pack fresh results with byte hashes while keeping historical failures intact."""
import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from verify_hanging_sign_front_holdout import record_file

ROOT = Path(__file__).resolve().parents[1]


def frame_controls(value):
    if isinstance(value, dict):
        if isinstance(value.get('capture'), dict) and value['capture'].get('backend') == 'Windows.Graphics.Capture':
            yield value
        else:
            for child in value.values():
                yield from frame_controls(child)
    elif isinstance(value, list):
        for child in value:
            yield from frame_controls(child)


def pack_run(directory):
    path = directory / 'report.json'
    original = json.loads(path.read_text(encoding='utf-8'))
    frozen_path = directory / 'frozen_source.json'
    after_path = directory / 'frozen_source_after.json'
    frozen = json.loads(frozen_path.read_text(encoding='utf-8'))
    registry_source = next(row for row in frozen['production']
                           if Path(row['path']).name == 'block_registry_data.py')
    after = json.loads(after_path.read_text(encoding='utf-8')) if after_path.exists() else {}
    frames = list(frame_controls(original))
    frame_reliability = bool(frames) and all(
        row['capture'].get('reliable') and row['capture'].get('background_safe') and
        row['capture'].get('native_resolution') and
        hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
        for row in frames)
    controlled = [row for row in frames if 'camera_unchanged' in row]
    controlled_stable = bool(controlled) and all(row['camera_unchanged'] and
        row['style_source_and_editor_state_unchanged'] for row in controlled)
    restored = original.get('restored', original.get('client_restored', False)) and not original.get('cleanup_errors')
    capture_cameras = [row for row in frames if 'camera_before' in row and 'camera_after' in row]
    recorded_cameras_stable = all(row['camera_before'] == row['camera_after'] for row in capture_cameras)
    accepted = bool(original.get('cases')) and original.get('completed', False) and original.get('passed', False) and restored and \
        after.get('production_and_tools_unchanged', False) and frame_reliability and \
        (controlled_stable if controlled else recorded_cameras_stable)
    if directory.name.startswith('chest-top-'):
        rendering_scope = 'world_projection_top_view_vs_native_world'
    elif 'actual-occupied' in directory.name:
        rendering_scope = 'world_projection_occupied_lifecycle'
    else:
        rendering_scope = 'actual_editor_viewport_and_world_projection_text_vs_native_world'
    cases = []
    recorded_registry = []
    if isinstance(original.get('native'), dict) and 'game_version' in original['native']:
        recorded_registry.append({key: original['native'][key] for key in ('game_version', 'palette_sha256')})
    for source in original.get('cases', []):
        case = {key: source[key] for key in ('id', 'view', 'name', 'direction', 'paired', 'passed') if key in source}
        if 'comparison' in source:
            case['comparison'] = source['comparison']
            case['native_pixels'] = source['native_signal']['pixels']
            case['public_fixture'] = source['public_source']['fixture']
            case['public_source_unchanged'] = source['public_source']['public_source_unchanged']
            case['document_preserved'] = source['document_preserved']
        if 'public_source' in source:
            native_registry = source['public_source']['native_client_document']['registry']
            recorded_registry.append({'game_version': native_registry['version'],
                                      'palette_sha256': native_registry['sha256']})
        for scope in ('native', 'editor', 'projection'):
            if scope in source and 'pixels' in source[scope]:
                case[scope] = {key: source[scope][key] for key in
                    ('pixels', 'panel_bounds', 'native_comparison', 'layout_comparison',
                     'blank_repeat_control', 'outside_text_control') if key in source[scope]}
        for key in ('positive_text_pixels', 'dynamic_state', 'initial_state', 'recovery_state',
                    'dynamic_control', 'initial_control', 'recovery_shape', 'recovery_layout'):
            if key in source:
                case[key] = source[key]
        cases.append(case)
    return {'name': directory.name, 'accepted': bool(accepted),
            'completed': original.get('completed', False), 'passed': original.get('passed', False),
            'restored': bool(restored), 'error': original.get('error'),
            'projection_mode': original.get('projection_mode'),
            'scope': original.get('scope', frozen['scope']),
            'rendering_scope': rendering_scope,
            'occupancy_source': original.get('occupancy_source'),
            'frame_count': len(frames), 'all_frames_reliable_background_wgc': frame_reliability,
            'controlled_frame_count': len(controlled), 'controlled_camera_and_style_stable': controlled_stable,
            'recorded_capture_camera_count': len(capture_cameras),
            'recorded_capture_cameras_stable': recorded_cameras_stable,
            'production_and_tools_unchanged_during_capture': after.get('production_and_tools_unchanged', False),
            'frozen_limits': frozen['limits'], 'cases': cases,
            'report': record_file(path), 'frozen_source': record_file(frozen_path),
            'frozen_registry_source': registry_source,
            'capture_recorded_registry': recorded_registry,
            'frozen_after': record_file(after_path) if after_path.exists() else None,
            'artifacts': [record_file(file) for file in sorted(directory.iterdir()) if file.is_file()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--review-index', type=Path,
                        default=ROOT / 'tools/data/entities_visual_viewed_frames_r8.json')
    parser.add_argument('--cleanup-audit', type=Path)
    parser.add_argument('--prior-cleanup-audit', type=Path, action='append', default=[])
    parser.add_argument('--stopped-session', type=Path)
    args = parser.parse_args()
    previous = ROOT / 'tools/data/entities_visual_unaccepted_evidence_r7.json'
    historical = json.loads(previous.read_text(encoding='utf-8'))
    registry_path = ROOT / 'tools/data/block_registry_manifest.json'
    registry = json.loads(registry_path.read_text(encoding='utf-8'))
    palette = record_file(ROOT / registry['source_file'])
    assert palette['sha256'].lower() == registry['source_sha256'].lower()
    runs = [pack_run(directory) for directory in sorted(args.artifacts.iterdir())
            if directory.is_dir() and directory.name.startswith(('sign-hanging-r8-', 'chest-top-r8-')) and
            (directory / 'report.json').exists() and (directory / 'frozen_source_after.json').exists()]
    generated_path = ROOT / 'behavior_pack/modern_projection/projection/block_registry_data.py'
    generated = record_file(generated_path)
    assert all(row['frozen_registry_source']['sha256'] == generated['sha256'] for row in runs)
    metadata = {}
    for node in ast.parse(generated_path.read_text(encoding='utf-8')).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('SOURCE_SHA256', 'SOURCE_VERSION'):
                metadata[name] = ast.literal_eval(node.value)
    assert metadata['SOURCE_SHA256'].lower() == palette['sha256'].lower()
    assert metadata['SOURCE_VERSION'] == registry['game_version']
    assert all(value['game_version'] == metadata['SOURCE_VERSION'] and
               value['palette_sha256'].lower() == metadata['SOURCE_SHA256'].lower()
               for row in runs for value in row['capture_recorded_registry'])
    accepted = [row for row in runs if row['accepted']]
    review = json.loads(args.review_index.read_text(encoding='utf-8'))
    reviewed_frames = []
    for run, names in review['runs'].items():
        for name in names:
            reviewed_frames.append(record_file(args.artifacts / run / name))
    runtime = {}
    if args.cleanup_audit:
        audit = json.loads(args.cleanup_audit.read_text(encoding='utf-8'))
        runtime['cleanup_audit'] = {'artifact': record_file(args.cleanup_audit),
            'completed': audit['completed'], 'restored': audit['restored'], 'read_only': audit['read_only']}
    if args.prior_cleanup_audit:
        runtime['prior_audits_preserved'] = [record_file(path) for path in args.prior_cleanup_audit]
    baseline = args.artifacts / 'chest-top-r8-baseline-plus8-v1/report.json'
    player_baseline = json.loads(baseline.read_text(encoding='utf-8'))['player']
    runtime['settled_player_baseline'] = {'foot': player_baseline['foot'],
        'can_fly': player_baseline['can_fly'], 'flying': player_baseline['flying'],
        'source': record_file(baseline),
        'initial_spawn_difference': 'First sign near-player record captured y=69 before grounding. Chest v1 and v4 both saved/restored y=68. The first final read-only audit with y=69 remains failed; no corrective teleport was applied.'}
    if args.stopped_session:
        session = json.loads(args.stopped_session.read_text(encoding='utf-8'))
        assert session['id'] == args.artifacts.parent.name
        assert session['owner'] == 'p0-entities-r8'
        assert session['state'] == 'stopped', session['state']
        runtime['stopped_session'] = record_file(args.stopped_session)
    manifest = {'schema': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(),
                'pack_tool': record_file(Path(__file__)),
                'game_version': registry['game_version'], 'palette_sha256': palette['sha256'].lower(),
                'palette_dump': palette, 'registry_manifest': record_file(registry_path),
                'registry_provenance': {'generated_source': generated,
                    'all_run_frozen_registry_bytes_match': True,
                    'frozen_artifacts': [row['frozen_source'] for row in runs],
                    'method': 'Every run froze block_registry_data.py before capture. Its verified unchanged bytes embed SOURCE_VERSION and SOURCE_SHA256. These values agree with the byte-verified palette dump and registry manifest; the manifest and dump were not separate capture-time freeze entries.'},
                'scope': 'Round eight independently frozen public entity visual controls',
                'production_changes_in_this_checkpoint': False,
                'accepted_scopes': [{'run': row['name'], 'scope': row['scope'],
                                     'rendering_scope': row['rendering_scope'],
                                     'projection_mode': row['projection_mode'],
                                     'cases': [{key: case[key] for key in ('id', 'view', 'name', 'direction', 'paired') if key in case}
                                               for case in row['cases']]} for row in accepted],
                'historical_failures': {'manifest': record_file(previous),
                    'original_sign': historical['signs']['original'],
                    'original_sign_offline': historical['signs']['original_offline'],
                    'final_r7_sign_holdout': historical['signs']['final_holdout'],
                    'final_r7_sign_offline': historical['signs']['final_offline'],
                    'r7_sign_failed_attempts': historical['signs']['failed_attempts'],
                    'r7_chest': historical['chest'],
                    'manual_body_diagnostic_accepted': False,
                    'reclassified': False},
                'oracle_change': 'Blank-only largest solid wood rectangle replaces merged row spans only in opt-in new holdouts; original color/layout/.45 gates retained; repeated blank and outside-native-text controls added.',
                'chest_candidate_008ca89_merged': False,
                'pending_scopes': ['Chest actual editor viewport native control',
                    'Chest species, wax and oxidation variants, directions and non-top views beyond recorded cases',
                    'Sign species, attachment directions and styles beyond the recorded public hanging-sign front/back fixture'],
                'limits': 'Case acceptance is limited to recorded public cells, states, styles, views and rendering modes. Sign oracle and native-camera test corrections are not production rendering changes.',
                'instance': {'id': args.artifacts.parent.name, 'owner': 'p0-entities-r8'},
                'visual_review': {'observer': review['observer'], 'index': record_file(args.review_index),
                                  'frames_actually_opened': reviewed_frames},
                'runtime_cleanup': runtime,
                'runs': runs}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'manifest': str(args.output.resolve()), 'accepted_runs': len(accepted), 'preserved_runs': len(runs)}))


if __name__ == '__main__':
    main()
