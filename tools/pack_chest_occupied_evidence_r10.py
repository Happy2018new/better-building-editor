"""Replay frozen occupied-chest PNGs offline and record the accepted scope."""
import argparse
import ast
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from PIL import Image

from pack_entity_visual_evidence_r8 import frame_controls
from verify_chest_occupied_frozen_holdout import (
    LIMITS, comparison, composite_signal, editor, restoration_matches)
from verify_hanging_sign_front_holdout import record_file

ROOT = Path(__file__).resolve().parents[1]
RUN = 'chest-occupied-r10-public-v1'
OWNER = 'entities-r10-background'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def normalized(value):
    return json.loads(json.dumps(value))


def original_gates(value, native_pixels):
    return (native_pixels >= LIMITS['minimum_native_pixels'] and
            value['shape_iou'] >= LIMITS['shape_iou'] and
            value['texture_cosine'] is not None and value['texture_cosine'] >= LIMITS['texture_cosine'] and
            value['scale_relative_error'] <= LIMITS['scale_relative_error'] and
            value['alignment']['center_distance_pixels'] <= LIMITS['center_distance_pixels'] and
            value['alignment']['boundary_rms_pixels'] <= LIMITS['boundary_rms_pixels'])


def state_matches(row, expected):
    return (row['active'] and row['ready'] and row['has_occupancy'] and row['tracked'] and
            row['state'] == expected and row['rendered'] == expected and
            (row['cache_slot'] < 0 if expected == 2 else row['cache_slot'] >= 0) and
            not any(row[key] for key in ('error', 'failed', 'preparing', 'building', 'pending', 'changed')) and
            row['document_preserved'] and row['history_preserved'])


def verify_capture(capture, path, session):
    frame = capture['frame']
    require(all(capture.get(key) for key in
                ('ok', 'reliable', 'background_only', 'native_resolution', 'background_safe', 'foreground_unchanged')),
            'Capture lacks a reliable background-only native frame')
    require(capture['backend'] == frame['backend'] == 'Windows.Graphics.Capture' and frame['ok'] and
            frame['native_resolution'] and frame['frame_qpc_100ns'] >= frame['request_qpc_100ns'],
            'Capture frame predates request or uses a different backend')
    require(capture['foreground_before'] == capture['foreground_after'] and
            capture['foreground_before']['pid'] != session['game_pid'], 'Capture changed foreground')
    require(capture['owner'] == session['owner'] == OWNER and
            capture['game_pid'] == session['game_pid'] and capture['game_identity'] == session['game_identity'],
            'Capture instance identity differs from owned session')
    require(record_file(path)['sha256'] == capture['sha256'], 'Capture PNG bytes changed: '+path.name)
    with Image.open(path) as image:
        require(image.size == (frame['width'], frame['height']) == (capture['width'], capture['height']),
                'PNG dimensions differ from captured native frame')


def replay_case(case, crop, half_crop, temporary):
    label = case['id']

    def extract(shown, hidden, roi, suffix, extractor=editor.extract):
        return extractor(shown['path'], hidden['path'], roi, temporary/(label+'_'+suffix+'.png'))

    double = extract(case['native_double'], case['native_empty'], crop, 'double')
    half = extract(case['native_double'], case['native_empty'], half_crop, 'half')
    single = extract(case['native_single'], case['native_single_empty'], half_crop, 'single')
    for key, signal in (('native_double_signal', double), ('native_logical_half_signal', half),
                        ('native_single_signal', single)):
        require(all(normalized(signal[2][name]) == case[key][name] for name in ('bbox', 'world_bounds', 'pixels', 'crop')),
                'Replayed native signal differs: '+label+'/'+key)
    values = {}
    for phase, key, reference, roi in (
            ('unoccupied', 'positive_comparison', double, crop),
            ('dynamic', 'dynamic_logical_half_comparison', half, half_crop),
            ('initial', 'initial_logical_half_comparison', half, half_crop),
            ('recovered', 'recovery_comparison', double, crop)):
        pair = case[phase]
        signal = extract(pair['screenshot'], pair['hidden_screenshot'], roi, phase)
        values[key] = comparison(reference, signal)
    assembly = extract(case['real_single_plus_ghost']['screenshot'], case['native_empty'], crop,
                       'assembly', composite_signal)
    require(all(normalized(assembly[2][name]) == case['composite_signal'][name]
                for name in ('bbox', 'world_bounds', 'pixels', 'crop')), 'Replayed assembly signal differs: '+label)
    values['single_versus_logical_half_diagnostic'] = comparison(single, half)
    values['composite_versus_native_double_diagnostic'] = comparison(double, assembly)
    require(all(normalized(value) == case[key] for key, value in values.items()),
            'PNG replay differs from original comparison: '+label)
    require(all(original_gates(values[key], reference[2]['pixels']) for key, reference in (
        ('positive_comparison', double), ('dynamic_logical_half_comparison', half),
        ('initial_logical_half_comparison', half), ('recovery_comparison', double))),
        'Lifecycle fails original visual gates: '+label)
    require(not values['single_versus_logical_half_diagnostic']['passed'] and
            values['composite_versus_native_double_diagnostic']['passed'],
            'Recorded diagnostic outcomes changed: '+label)
    return {'id': label, 'name': case['name'], 'direction': case['direction'], 'paired': case['paired'],
            'fixture': case['fixture'], 'cells': case['cells'], 'passed_original_lifecycle_gates': True,
            'native_double_pixels': double[2]['pixels'], 'native_logical_half_pixels': half[2]['pixels'],
            'comparisons_recomputed_from_pngs': values, 'diagnostic_assembly_accepted': False}


def pack(artifacts, session_path, review_path):
    directory = artifacts/RUN
    report, frozen = load(directory/'report.json'), load(directory/'frozen_source.json')
    after, session = load(directory/'frozen_source_after.json'), load(session_path)
    require(session['id'] == artifacts.parent.name and session['state'] == 'stopped', 'Owned session is not stopped')
    require(session['noactivation']['background_safe'] and session['noactivation']['window_noactivate'] and
            session['foreground_unchanged'] and session['foreground_before_still_valid'], 'Startup foreground guard failed')
    require(report['limits'] == frozen['limits'] == LIMITS, 'Original visual gates changed')
    require(report['completed'] and report['passed'] and report['restored'] and not report.get('cleanup_errors') and
            after['production_and_tools_unchanged'], 'Native holdout or restoration did not pass')
    require(report['runtime_config'] == frozen['config'] and report['render_path'] == 'missing_projection' and
            report['logical_pair_policy_preserved'], 'Runtime scope/config differs from frozen declaration')
    require(report['calibration'] == load(directory/'remaining_target_bounds_before_chests.json'),
            'Remaining-cell bounds differ from pre-chest declaration')
    require(report['grounded_baseline'] == load(directory/'grounded_baseline_before_mutation.json'),
            'Grounded baseline differs from pre-mutation record')
    restoration = load(directory/'restoration_audit.json')
    require(restoration == report['restoration_audit'] and restoration['passed'] and restoration['read_only'] and
            restoration_matches(restoration['baseline'], restoration['observed']), 'Player restoration audit failed')
    cleanup_path = artifacts/'entities-r10-final-cleanup-audit.json'
    cleanup = load(cleanup_path)
    require(cleanup['completed'] and cleanup['restored'] and cleanup['read_only'] and
            not cleanup['client']['temporary_flags'] and not cleanup['server']['temporary_flags'] and
            not any(cleanup['client'][key] for key in
                    ('projection_active', 'preparing', 'entity', 'entities', 'workspace_open', 'transition')) and
            restoration_matches(report['grounded_baseline'], cleanup['player']), 'Final read-only cleanup audit failed')
    registry_path = ROOT/'tools/data/block_registry_manifest.json'
    registry = load(registry_path)
    palette = record_file(ROOT/registry['source_file'])
    generated = ROOT/'behavior_pack/modern_projection/projection/block_registry_data.py'
    metadata = {node.targets[0].id: ast.literal_eval(node.value) for node in ast.parse(generated.read_text(encoding='utf-8')).body
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) and
                node.targets[0].id in ('SOURCE_VERSION', 'SOURCE_SHA256')}
    require(metadata['SOURCE_VERSION'] == registry['game_version'] and
            metadata['SOURCE_SHA256'].lower() == registry['source_sha256'].lower() == palette['sha256'],
            'Palette, generated registry and manifest provenance differ')
    frozen_registry = next(row for row in frozen['production'] if Path(row['path']).name == generated.name)
    require(frozen_registry['sha256'] == record_file(generated)['sha256'], 'Frozen registry source differs')
    oracle_names = ('verify_chest_occupied_frozen_holdout.py', 'verify_chest_editor_frozen_holdout.py',
                    'verify_copper_chest_render.py', 'shulker_pixels.py', 'verify_camera_projection.py',
                    'verify_missing_neighbor_visuals.py')
    oracle_sources = [record_file(ROOT/'tools'/name) for name in oracle_names]
    require(all(any(Path(row['path']).name == Path(source['path']).name and row['sha256'] == source['sha256']
                    for row in frozen['tools']) for source in oracle_sources), 'Offline oracle differs from capture-time tool')
    frames = list(frame_controls(report))
    require(len(frames) == 30, 'Expected 30 native full-frame controls')
    for row in frames:
        path = Path(row['path'])
        verify_capture(row['capture'], path, session)
        require(row['sha256'] == row['capture']['sha256'] and row['capture'] == load(path.with_suffix('.capture.json')),
                'Report and standalone capture metadata differ: '+path.name)
        if 'camera_before' in row:
            require(row['camera_before'] == row['camera_after'], 'Native capture camera changed')
    cases = []
    with tempfile.TemporaryDirectory(prefix='chest-occupied-r10-replay-') as temporary:
        temporary = Path(temporary)
        calibration = report['calibration']
        crop = tuple(int(value*calibration['shown']['size'][axis % 2])
                     for axis, value in enumerate(frozen['world_signal_roi']))
        cube = editor.extract(calibration['shown']['path'], calibration['empty']['path'], crop, temporary/'cube.png')
        half_crop = tuple(cube[2]['world_bounds'])
        require(list(half_crop) == calibration['remaining_target_bounds'], 'Independent cube bounds changed')
        require(len(report['cases']) == 2, 'Expected fixed ordinary/copper public double cases')
        for case, declared in zip(report['cases'], frozen['config']['cases'][1:]):
            require(all(case[key] == value for key, value in declared.items()) and case['public_source']['public_source_unchanged'],
                    'Public source case differs from frozen declaration')
            require(case['public_source']['native_client_document']['registry'] ==
                    {'version': registry['game_version'], 'sha256': palette['sha256']}, 'Runtime registry provenance differs')
            require(calibration['empty']['capture']['finished_at'] < case['native_double']['capture']['started_at'],
                    'Cube declaration was not captured before chest reference')
            require(case['stone_write']['after']['name'] == 'minecraft:stone' and
                    case['stone_clear']['after']['name'] == 'minecraft:air' and
                    case['stone_write']['pos'] == case['stone_clear']['pos'] == case['native_double_placement']['cells'][1],
                    'Real stone did not occupy and clear the declared sub-half')
            for key, expected in (('unoccupied_state', (1, 1)), ('dynamic_state', (1, 2)),
                                  ('initial_state', (1, 2)), ('recovery_state', (1, 1)), ('composite_state', (2, 1))):
                require(len(case[key]) == 2 and all(state_matches(row, value) for row, value in zip(case[key], expected)),
                        'Occupancy/document/history lifecycle state failed: '+key)
            for phase in ('unoccupied', 'dynamic', 'initial', 'recovered', 'real_single_plus_ghost'):
                pair = case[phase]
                require(pair['state_before'] == pair['state_after'] and pair['camera_before'] == pair['camera_after'],
                        'Hide/show control changed state or camera: '+phase)
            cases.append(replay_case(case, crop, half_crop, temporary))
    review = load(review_path)
    names = review['runs'][RUN]
    require(len(names) == len(set(names)) == 30 and set(names) == {Path(row['path']).name for row in frames},
            'Viewed-frame index does not cover all full PNG controls exactly once')
    preflight_path = artifacts/'entities-r10-preflight.png'
    verify_capture(load(preflight_path.with_suffix('.capture.json')), preflight_path, session)
    require(review['preflight'] == [preflight_path.name], 'Preflight review entry differs')
    return {'schema': 1, 'recorded_at': datetime.now(timezone.utc).isoformat(), 'accepted': True,
            'pack_tool': record_file(Path(__file__)), 'production_rendering_changed': False,
            'scope': report['scope'], 'render_path': report['render_path'], 'top_view_only': True,
            'occupancy_source': report['occupancy_source'], 'occupied_logical_half': 'sub/right',
            'oracle': frozen['oracle'], 'original_gates': LIMITS, 'png_replay_matches_original_report': True,
            'game_version': registry['game_version'], 'state_count': registry['record_count'],
            'palette_dump': palette, 'registry_manifest': record_file(registry_path), 'frozen_registry_source': frozen_registry,
            'offline_oracle_sources': oracle_sources, 'all_30_frames_fresh_reliable_background_wgc': True,
            'document_history_camera_and_public_source_preserved': True,
            'visual_review': {'observer': review['observer'], 'index': record_file(review_path),
                              'frames_actually_opened': [record_file(directory/name) for name in names],
                              'preflight_actually_opened': record_file(preflight_path)},
            'runtime_cleanup': {'audit': record_file(cleanup_path), 'restoration': restoration,
                                'stopped_session': record_file(session_path), 'no_corrective_audit_teleport': True,
                                'startup_guard': session['noactivation'],
                                'handle_observation': {'audit_before': cleanup['process'], 'audit_after': cleanup['process_after'],
                                    'instance_stopped_after_quiet_growth': True, 'cause_attributed': False}},
            'historical_evidence_reclassified': False, 'chest_candidate_008ca89_merged': False,
            'diagnostic_boundary': 'Native singles differ from logical double halves; real single plus ghost has a visible central gap and copper texture mismatch despite aggregate shape gates.',
            'pending_scopes': ['Main-half stone occupancy lifecycle', 'Arbitrary real chest completion',
                               'Other chest materials, directions and non-top views', 'Head/frame/banner visible item content'],
            'cases': cases, 'artifacts': [record_file(path) for path in sorted(directory.iterdir()) if path.is_file()]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('artifacts', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--review-index', type=Path, default=ROOT/'tools/data/entities_visual_viewed_frames_r10.json')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh manifest path; raw evidence is never overwritten')
    result = pack(args.artifacts, args.session, args.review_index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=True, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'accepted': result['accepted'], 'replayed_cases': len(result['cases']), 'reviewed_native_frames': 30}))


if __name__ == '__main__':
    main()
