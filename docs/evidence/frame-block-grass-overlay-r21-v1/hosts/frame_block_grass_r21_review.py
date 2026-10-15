"""Review only fresh, completed and restored grass phase pixels offline."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / '.runtime/frame-block-grass-overlay-r21-control-v1'
BUNDLE = ROOT / 'docs/evidence/frame-block-light-holdout-r21-v1'
sys.path.insert(0, str(BUNDLE / 'sources/analysis/tools'))
from item_sprite_capture_contract import snapshot_sources, snapshot_digest
from analyze_liquid_workspace import capture_failures
from verify_camera_projection import analyze_calibration


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


def setup(phase_id):
    plan = json.loads((CONTROL / 'plan.json').read_bytes())
    assert sha(Path(__file__)) == plan['reviewer_sha256']
    assert sha(ROOT / '.runtime/frame_block_grass_r21_run.py') == plan['launcher_sha256']
    assert sha(BUNDLE / 'manifest.json') == plan['analysis_manifest_sha256']
    manifest = json.loads((BUNDLE / 'manifest.json').read_bytes())
    for relative, expected in manifest['files'].items():
        if relative.startswith('sources/analysis/') or relative == 'replay.py':
            assert sha(BUNDLE / relative) == expected, relative
    for name in ('candidate', 'source-textures'):
        assert sha(CONTROL / (name + '.json')) == plan[name.replace('-', '_') + '_sha256']
    project = Path(plan['project'])
    assert snapshot_digest(snapshot_sources(project)) == plan['source_sha256']
    assert sha(project / '.mcdev.json') == plan['configuration_sha256']
    phase = next(row for row in plan['phases'] if row['id'] == phase_id)
    assert sha(CONTROL / phase['matrix']) == phase['matrix_sha256']
    batch = json.loads((CONTROL / phase['matrix']).read_bytes())
    assert len(batch['cases']) == 1
    request = batch['cases'][0]
    assert request['item'] == ['minecraft:grass_block', 0]
    assert request['view_angle_degrees'] == phase['angle']
    assert not request['artificially_enchanted']
    return plan, phase, batch


def run(args):
    plan, phase, batch = setup(args.phase)
    report_path = Path(phase['capture_output']) / 'report.json'
    if args.check:
        return {'read_only': True, 'phase': args.phase, 'started': False,
            'planned_source_sha256': plan['source_sha256'], 'report_exists': report_path.exists(),
            'frozen_analysis_helpers_verified': True, 'runtime_action': False,
            'production_qualified': False, 'appearance_accepted': False}
    outcome_path = CONTROL / (args.phase + '-outcome.json')
    assert report_path.is_file() and outcome_path.is_file(), 'Phase has not completed'
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    outcome = json.loads(outcome_path.read_bytes())
    assert outcome['phase'] == args.phase and outcome['phase_ready_for_review']
    assert outcome['report_sha256'] == sha(report_path)
    assert outcome['host_wrapper_sha256'] == plan['capture_host_sha256']
    assert outcome['completed'] and outcome['matrix_completed'] and outcome['within_180_seconds']
    assert outcome['source_unchanged'] and not outcome['cleanup_errors']
    assert outcome['native_references_restored']
    environment = outcome['environment']
    assert environment == json.loads((CONTROL / (args.phase + '-environment.json')).read_bytes())
    assert environment['setup_readback_passed'] is True
    assert environment['restored_by_original_environment_helper'] is True
    readback = environment['setup_readback']
    assert readback['time'] % 24000 == phase['time_of_day'] == 6000
    assert not any(readback[key] for key in ('raining', 'thunder', 'daylight_cycle', 'weather_cycle'))
    assert report['completed'] and report['matrix_completed'] and report['environment_restored']
    assert report['source_unchanged'] and not report['cleanup_errors']
    assert report['launch_sources'] == report['sources_after'] == plan['sources']
    assert snapshot_digest(report['launch_sources']) == report['launch_sources_sha256'] == plan['source_sha256']
    assert report['frame_block_batch']['sha256'] == phase['matrix_sha256']
    assert report['frame_block_batch']['data'] == batch
    assert report['candidate_geometry']['sha256'] == plan['candidate_sha256']
    candidate = json.loads((CONTROL / 'candidate.json').read_bytes())
    assert report['candidate_geometry']['data'] == candidate
    assert report['resource_contract']['resource_sha256'] == candidate['resource_sha256']
    assert not report.get('native_item_shader_errors')
    request = batch['cases'][0]
    expected_id = 'orientation.block.' + request['id']
    assert report['requested_cases'] == [expected_id] and not report['remaining_cases']
    assert len(report['cases']) == 1
    case = report['cases'][0]
    assert case['id'] == expected_id and case['measurement_completed']
    assert case['native_reference']['restored']
    assert all(case['source'][key] == request[key]
        for key in ('item', 'view_angle_degrees', 'artificially_enchanted'))
    assert case['source']['facing'] == 2 and case['source']['rotation_degrees'] == 0
    saved = json.loads((CONTROL / 'ready-summary.json').read_bytes())
    assert report['session']['owner'] == plan['owner']
    for key in ('id', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'session_file'):
        assert report['session'][key] == saved[key], key
    calibration = report['camera_calibration']
    assert calibration['passed'] and calibration['restored'] and not calibration['cleanup_errors']
    labels = {row['label'] for row in report['captures']}
    assert len(labels) == len(report['captures']) == 14
    for route in ('editor', 'native', 'full', 'missing'):
        for control in ('hidden_before', 'shown', 'hidden_after'):
            assert expected_id + '_' + route + '_' + control in labels
    receipts = [row['capture'] for row in report['captures']]
    receipts += [row[mode] for row in calibration['views'] for mode in ('shown', 'hidden')]
    assert len(receipts) == 20
    assert not capture_failures({str(i): row for i, row in enumerate(receipts)}, report['session'])
    attempt = json.loads((CONTROL / (args.phase + '-attempt.json')).read_bytes())
    first = datetime.fromisoformat(attempt['at'])
    for receipt in receipts:
        path = Path(receipt['path']).resolve()
        assert path.is_relative_to(report_path.parent.resolve()), 'Old or external pixels rejected'
        assert datetime.fromisoformat(receipt['started_at']) >= first, 'Pixels predate the phase attempt'
        assert sha(path) == receipt['sha256']
    assert not args.output.exists(), 'Use a fresh review directory'
    args.output.mkdir(parents=True)
    (args.output / 'source-report.json').write_bytes(report_bytes)
    reconstructed = deepcopy(calibration)
    for row in reconstructed['views']:
        row['signal'] = str(args.output / ('camera-' + row['view'] + '-signal.png'))
        row['outline_comparison'] = str(args.output / ('camera-' + row['view'] + '-outline.png'))
    analyze_calibration(reconstructed)
    spec = importlib.util.spec_from_file_location('grass_light_review_helpers', BUNDLE / 'replay.py')
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    for key in ('passed', 'vertical_fov', 'individual_fitted_vertical_fov'):
        helpers.compare(calibration[key], reconstructed[key], 'calibration/' + key)
    for expected, actual in zip(calibration['views'], reconstructed['views']):
        helpers.compare(expected['fit'], actual['fit'], 'calibration/' + actual['view'])
    result = helpers.review(report, candidate['pose'], args.output / 'analysis')
    result.update(schema=1, phase=args.phase, ready=True, read_only=True,
        source_report_sha256=sha(report_path), runtime_outcome_sha256=sha(outcome_path),
        reviewer_sha256=sha(Path(__file__)), planned_source_sha256=plan['source_sha256'],
        analysis_manifest_sha256=plan['analysis_manifest_sha256'], batch_completed=True,
        native_reference_restored=True, environment_restored=True, raw_png_count=len(receipts),
        fresh_capture_paths_and_timestamps_verified=True, calibration_reproduced=True,
        production_qualified=False, appearance_accepted=False, raw_color_fitting_or_registration=False,
        limits=['Root must open fresh native/full/missing raw images and montage before scheduling oblique phases',
            'Review readiness does not accept appearance, light factor, production or alpha',
            'No game, capture, retry or next phase is started by this reader'])
    result['review_images_sha256'] = {path.relative_to(args.output).as_posix(): sha(path)
        for path in args.output.rglob('*.png')}
    save(args.output / 'review.json', result)
    assert snapshot_digest(snapshot_sources(Path(plan['project']))) == plan['source_sha256']
    return {key: result[key] for key in ('phase', 'ready', 'batch_completed', 'raw_png_count',
        'calibration_reproduced', 'production_qualified', 'appearance_accepted')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase', choices=('front', 'left75', 'right75'), default='front')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.check and args.output is None:
        parser.error('Review requires a fresh --output directory')
    print(json.dumps(run(args)))
