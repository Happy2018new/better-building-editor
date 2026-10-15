"""Read-only first-window image review; no runtime calls or source edits."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / '.runtime/frame-block-r21-light-holdout-control-v1'
BUNDLE = ROOT / 'docs/evidence/frame-block-appearance-r21-v1'
FROZEN = BUNDLE / 'sources/tools'
sys.path.insert(0, str(FROZEN))
import analyze_frame_block_multiview_r21 as geometry
import analyze_frame_block_appearance_r21 as appearance
from item_sprite_capture_contract import snapshot_digest, snapshot_sources
from camera_projection import project_points

PHASE = 'noon-grass-log'
ROUTES = ('native', 'full', 'missing')
CONTROLS = ('hidden_before', 'shown', 'hidden_after')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def setup():
    plan = json.loads((CONTROL / 'plan.json').read_bytes())
    assert snapshot_digest(snapshot_sources(Path(plan['project']))) == plan['source_sha256']
    assert digest(ROOT / '.runtime/frame_block_light_r21_run.py') == plan['launcher_sha256']
    assert digest(CONTROL / 'candidate.json') == plan['candidate_sha256']
    phase = next(row for row in plan['phases'] if row['id'] == PHASE)
    batch = json.loads((CONTROL / phase['matrix']).read_bytes())
    assert digest(CONTROL / phase['matrix']) == phase['matrix_sha256']
    assert [(row['item'], row['view_angle_degrees']) for row in batch['cases']] == [
        (['minecraft:grass_block', 0], -40), (['minecraft:oak_log', 0], 35)]
    assert not any(row['artificially_enchanted'] for row in batch['cases'])
    manifest = json.loads((BUNDLE / 'manifest.json').read_bytes())
    for relative, expected in manifest['files'].items():
        if relative.startswith('sources/') and (BUNDLE / relative).suffix == '.py':
            assert digest(BUNDLE / relative) == expected, relative
    return plan, phase, batch


def run(args):
    plan, phase, batch = setup()
    report_path = Path(phase['capture_output']) / 'report.json'
    expected_ids = ['orientation.block.' + row['id'] for row in batch['cases']]
    if args.check:
        return {'read_only': True, 'phase': PHASE, 'source_unchanged': True,
            'source_sha256': plan['source_sha256'], 'cases': batch['cases'],
            'capture_report_exists': report_path.exists(), 'will_capture_or_launch': False,
            'frozen_review_helpers_verified': True, 'production_qualified': False}
    if not report_path.exists():
        return {'ready': False, 'reason': 'First holdout report does not exist',
            'expected_report': str(report_path), 'runtime_action': False}
    report_bytes = report_path.read_bytes()
    report = json.loads(report_bytes)
    assert report['launch_sources_sha256'] == plan['source_sha256']
    assert snapshot_digest(report['launch_sources']) == plan['source_sha256']
    assert report['requested_cases'] == expected_ids, 'Unexpected capture cases'
    assert report['frame_block_batch']['sha256'] == phase['matrix_sha256']
    assert report['frame_block_batch']['data'] == batch
    assert report['candidate_geometry']['sha256'] == plan['candidate_sha256']
    assert report['session']['owner'] == plan['owner']
    assert not report.get('native_item_shader_errors')
    calibration = report['camera_calibration']
    assert calibration['passed'] and calibration['restored'] and not calibration['cleanup_errors']
    captures = {row['label']: row for row in report['captures']}
    cases = {row['id']: row for row in report['cases']}
    assert len(captures) == len(report['captures']), 'Duplicate capture labels'
    assert len(cases) == len(report['cases']), 'Duplicate case IDs'
    selected = expected_ids if args.all else expected_ids[:1]
    missing = [identity + '_' + route + '_' + control for identity in selected
        for route in ROUTES for control in CONTROLS
        if identity + '_' + route + '_' + control not in captures]
    incomplete = [identity for identity in selected if identity not in cases
        or not cases[identity].get('measurement_completed')
        or not cases[identity].get('native_reference', {}).get('restored')]
    if missing or incomplete:
        return {'ready': False, 'reason': 'Wait for complete restored hidden/shown controls',
            'missing_capture_labels': missing, 'incomplete_cases': incomplete, 'runtime_action': False}
    if report.get('completed'):
        assert report['matrix_completed'] and report['source_unchanged'] and not report['cleanup_errors']
        assert report['launch_sources'] == report['sources_after']
    candidate = json.loads((CONTROL / 'candidate.json').read_bytes())
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'source-report.json').write_bytes(report_bytes)
    result = {'schema': 1, 'ready': True, 'read_only': True, 'phase': PHASE,
        'source_report_sha256': hashlib.sha256(report_bytes).hexdigest(),
        'reviewer_sha256': digest(Path(__file__)), 'review_helper_manifest_sha256': digest(BUNDLE / 'manifest.json'),
        'planned_source_sha256': plan['source_sha256'], 'case_count': len(selected),
        'production_qualified': False, 'appearance_accepted': False,
        'raw_color_fitting_or_registration': False, 'batch_completed': bool(report.get('completed')),
        'geometry_thresholds': geometry.LIMITS, 'cases': [],
        'limits': ['Quick review does not accept appearance, alpha, lighting, texture, depth or production',
            'RGB errors use the same unregistered screen pixels without gain fitting',
            'Filled and unfilled difference masks are both retained; filled gaps alone do not prove alpha loss',
            'First-case preview may precede complete batch cleanup and runtime outcome',
            'No later capture group is scheduled by this reader']}
    for identity in selected:
        case = cases[identity]
        request = batch['cases'][expected_ids.index(identity)]
        assert all(case['source'][key] == request[key]
            for key in ('item', 'view_angle_degrees', 'artificially_enchanted'))
        assert case['source']['id'] == request['orientation']
        assert case['source']['facing'] == 2 and case['source']['rotation_degrees'] == 0
        selected_captures = {label: row for label, row in captures.items()
            if any(label == identity + '_' + route + '_' + control for route in ROUTES for control in CONTROLS)}
        assert not geometry.capture_failures({label: row['capture'] for label, row in selected_captures.items()}, report['session'])
        views = {route: geometry.observe(case, route, captures, calibration['vertical_fov']) for route in ROUTES}
        common = np.logical_and.reduce([views[route]['mask'] for route in ROUTES])
        regions = appearance.face_regions(views['native']['position'], candidate['pose'],
            views['native']['camera'], views['native']['size'], calibration['vertical_fov'], common, project_points)
        images = {route: Image.fromarray(views[route]['shown'].astype(np.uint8)) for route in ROUTES}
        row = {'angle': case['source']['view_angle_degrees'], 'images': images, 'mask': common, 'regions': regions}
        item = case['source']['item'][0].split(':')[-1]
        appearance.draw_montage([row], args.output / (item + '-native-full-missing.png'))
        appearance.draw_montage([row], args.output / (item + '-face-rois.png'), annotated=True)
        measured = {'id': identity, 'item': case['source']['item'],
            'angle': row['angle'], 'native_reference_restored': True,
            'paired_filled_silhouettes': {route: geometry.paired(views['native'], views[route]) for route in ('full', 'missing')},
            'unfilled_differences': {}, 'faces': {}}
        raw_masks = {}
        for route, view in views.items():
            before = geometry.rgb(captures[identity + '_' + route + '_hidden_before']['capture']['path'])
            after = geometry.rgb(captures[identity + '_' + route + '_hidden_after']['capture']['path'])
            envelope = np.zeros(common.shape, dtype=bool)
            envelope[view['lo'][1]:view['hi'][1], view['lo'][0]:view['hi'][0]] = True
            stable = np.max(np.abs(before - after), axis=2) <= 3
            raw = geometry.difference_mask(view['shown'], (before.astype(float) + after)/2., envelope, 8) & stable
            raw_masks[route] = raw
            measured['unfilled_differences'][route] = {'pixels': int(raw.sum()),
                'filled_pixels': int(view['mask'].sum()), 'filled_extra_pixels': int((view['mask'] & ~raw).sum())}
            Image.fromarray(raw).save(args.output / (item + '-' + route + '-unfilled-mask.png'))
            Image.fromarray(view['mask']).save(args.output / (item + '-' + route + '-filled-mask.png'))
        measured['paired_unfilled_iou'] = {route: float((raw_masks['native'] & raw_masks[route]).sum()
            / max(1, int((raw_masks['native'] | raw_masks[route]).sum()))) for route in ('full', 'missing')}
        for face, region in regions.items():
            mask = region['mask']
            pixels = {route: views[route]['shown'][mask].astype(np.uint8) for route in ROUTES}
            measured['faces'][face] = {'roi_pixels': int(mask.sum()), 'large_roi': int(mask.sum()) >= 64,
                'routes': {route: appearance.color_summary(values) for route, values in pixels.items()},
                'native_product': {route: appearance.color_pair(pixels['native'], pixels[route]) for route in ('full', 'missing')}}
            Image.fromarray(mask).save(args.output / (item + '-' + face + '-roi.png'))
        result['cases'].append(measured)
    outcome = CONTROL / (PHASE + '-outcome.json')
    result['runtime_outcome'] = json.loads(outcome.read_bytes()) if outcome.exists() else None
    assert snapshot_digest(snapshot_sources(Path(plan['project']))) == plan['source_sha256']
    (args.output / 'review.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    return {key: result[key] for key in ('ready', 'case_count', 'batch_completed', 'production_qualified', 'appearance_accepted')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--all', action='store_true', help='Review both existing first-batch cases, without taking screenshots')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if not args.check and args.output is None:
        parser.error('Image review requires a fresh --output directory')
    print(json.dumps(run(args)))
