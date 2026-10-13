"""Replay water product geometry and transparency controls; no native parity gate."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from camera_projection import project_points
from water_capture_contract import camera_matches, calibrated_viewport_matches, scene_capture_state, scene_pose

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.camera import OrbitCamera

LIMITS = {'rgb_delta': 8, 'minimum_water_pixels': 24, 'minimum_mask_iou': .80,
          'maximum_boundary_pixels': 6, 'minimum_contribution_pixels': 8,
          'minimum_contribution_fraction': .10, 'temporal_delta': 2}
FACE_INDICES = ((4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
                (3, 0, 4, 7), (1, 2, 6, 5), (3, 2, 1, 0))


def water_polygons(shapes):
    for shape in shapes:
        x, y, z = shape['position']
        heights = [int(value * 255 + .5) / 255. for value in shape['heights']]
        points = [(x + dx, y, z + dz) for dx, dz in ((0, 0), (1, 0), (1, 1), (0, 1))]
        points.extend((x + dx, y + heights[index], z + dz)
                      for index, (dx, dz) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))))
        for face, corners in enumerate(FACE_INDICES):
            if shape['faces'] & (1 << face):
                yield shape, tuple(points[index] for index in corners)


def scene_project(points, shape, state):
    origin = tuple(axis // 4 * 4 for axis in shape['position'])
    groups = state['liquid_groups']
    identities = {row['key'] for row in groups if tuple(row['origin']) == origin}
    controls = [row for row in state['liquid_control_requests'] if row['key'] in identities
                and row['poses'] and any(row['visible'])]
    if not controls:
        raise ValueError('Water shape has no visible native control')
    row = controls[0]
    slot = row['visible'].index(True)
    position, size, pose = row['doll_positions'][slot], row['doll_sizes'][slot], row['poses'][slot]
    unit = pose[0] * min(size)
    center = (position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / 4.)
    camera = OrbitCamera(*state['camera_pose'])
    right, up, unused = camera.basis()
    result = []
    for point in points:
        offset = tuple(point[i] - origin[i] - 2. for i in range(3))
        result.append((center[0] + unit * sum(offset[i] * right[i] for i in range(3)),
                       center[1] - unit * sum(offset[i] * up[i] for i in range(3))))
    return result


def project(points, shape, row, source, size):
    if row['route'] == 'editor':
        points = scene_project(points, shape, row['ready'])
        engine = row['ready']['screen_size']
        return [(point[0] * size[0] / engine[0], point[1] * size[1] / engine[1]) for point in points]
    camera = row['camera']
    origin = row['ready']['origin']
    points = [tuple(point[i] + origin[i] for i in range(3)) for point in points]
    projected = project_points(points, camera['position'], camera['target'], size,
                               source['camera_calibration']['vertical_fov'])
    return [(point['screenX'], point['screenY']) for point in projected]


def expected_mask(row, source, size):
    image = Image.new('L', size)
    draw = ImageDraw.Draw(image)
    for shape, polygon in water_polygons(row['ready']['shapes']):
        draw.polygon(project(polygon, shape, row, source, size), fill=255)
    return np.asarray(image) > 0


def region_mask(row, source, size, points):
    shape = next(shape for shape in row['ready']['shapes'] if tuple(shape['position']) == (3, 3, 3))
    mapped = project(points, shape, row, source, size)
    image = Image.new('L', size)
    ImageDraw.Draw(image).polygon(mapped, fill=255)
    return np.asarray(image) > 0


def product_geometry(actual, expected):
    a, e = mask_row(actual), mask_row(expected)
    union = int(np.count_nonzero(actual | expected))
    iou = int(np.count_nonzero(actual & expected)) / max(1, union)
    edge = max(abs(x - y) for x, y in zip(a['bounds'], e['bounds'])) if a['bounds'] and e['bounds'] else None
    return {'observed': a, 'declared': e, 'iou': iou, 'maximum_boundary_pixels': edge,
            'passed': bool(a['pixels'] >= LIMITS['minimum_water_pixels'] and iou >= LIMITS['minimum_mask_iou']
                           and edge is not None and edge <= LIMITS['maximum_boundary_pixels'])}


def contribution(first, second, eligible, threshold=None):
    threshold = LIMITS['rgb_delta'] if threshold is None else threshold
    changed = difference_mask(first, second, eligible, threshold)
    pixels = int(changed.sum())
    total = int(eligible.sum())
    return {'eligible_pixels': total, 'contribution_pixels': pixels, 'rgb_delta': threshold, 'fraction': pixels / max(1, total),
            'passed': bool(pixels >= LIMITS['minimum_contribution_pixels']
                           and pixels / max(1, total) >= LIMITS['minimum_contribution_fraction'])}


def analyze(path):
    source = json.loads(path.read_bytes())
    failures = capture_failures(source['captures'], source['session_binding'])
    inputs = source.get('source_file_sha256_before')
    if (not isinstance(inputs, dict) or not inputs or source.get('source_unchanged') is not True
            or inputs != source.get('source_file_sha256_after') or inputs != source.get('launch_source_sha256')
            or source.get('source_contract_sha256') != hashlib.sha256(
                json.dumps(inputs, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()):
        failures.append('Source/resource snapshot was absent, changed or inconsistent with the game launch')
    sizes = {(row.get('width'), row.get('height')) for row in source['captures'].values()}
    if len(sizes) > 1:
        failures.append('Capture dimensions changed during the paired controls')
    missing = sorted(set(source['rows']) - set(source['captures']))
    if missing:
        failures.append({'missing_row_captures': missing})
    for label, row in source['rows'].items():
        if row.get('route') == 'editor':
            if (row.get('scene_before') is None or row.get('scene_after') is None
                    or row['scene_before'] != row['scene_after']
                    or row['scene_before'] != scene_capture_state(row.get('ready'))):
                failures.append({'scene_layout_drift': label})
            wet = source['rows'].get(row['route'] + '_' + row['case'] + '_wet')
            if wet and (scene_pose(row.get('ready')) is None
                        or scene_pose(row.get('ready')) != scene_pose(wet.get('ready'))):
                failures.append({'paired_scene_pose_drift': label})
            continue
        fields = ('camera_expected', 'camera', 'camera_before', 'camera_after')
        if any(not isinstance(row.get(field), dict) for field in fields):
            failures.append({'camera_evidence_missing': label})
            continue
        expected = row['camera_expected']
        if any(not camera_matches(row[field], expected) for field in fields[1:]):
            failures.append({'camera_drift': label})
        if not calibrated_viewport_matches(row['camera'], source.get('camera_calibration', {})):
            failures.append({'calibrated_viewport_drift': label})
        wet = source['rows'].get(row['route'] + '_' + row['case'] + '_wet')
        if wet and (not isinstance(wet.get('camera'), dict) or not camera_matches(row['camera'], wet['camera'])):
            failures.append({'paired_camera_drift': label})
    for label, frame in source['captures'].items():
        if label.startswith('editor_'):
            if frame.get('scene_before') is None or frame.get('scene_before') != frame.get('scene_after'):
                failures.append({'frame_scene_layout_drift': label})
            continue
        if not label.startswith(('full_', 'missing_')):
            continue
        fields = ('camera_expected', 'camera_before', 'camera_after')
        if any(not isinstance(frame.get(field), dict) for field in fields):
            failures.append({'frame_camera_evidence_missing': label})
        elif any(not camera_matches(frame[field], frame['camera_expected']) for field in fields[1:]):
            failures.append({'frame_camera_drift': label})
        elif (not calibrated_viewport_matches(frame['camera_after'], source.get('camera_calibration', {}))
              or [frame['width'], frame['height']] != source.get('camera_calibration', {}).get('capture_size')):
            failures.append({'frame_calibrated_viewport_drift': label})
    for route in source.get('routes', ()):
        for case in source.get('cases', ()):
            for control in source.get('controls', ('wet',)):
                if not case.startswith('wet_') and control not in ('wet', 'dry'):
                    continue
                label = route + '_' + case + '_' + control
                if label not in source['rows']:
                    failures.append({'missing_requested_row': label})
    evidence_valid = (not failures and source['completed'] is True and source['restored'] is True
                      and not source['cleanup_errors'])
    output = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'limits': LIMITS,
              'completed': source['completed'], 'restored': source['restored'], 'cleanup_errors': source['cleanup_errors'],
              'capture_failures': failures, 'captures_verified': not failures, 'geometry': {}, 'transparency': {},
              'animation': {}, 'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'product_style_accepted': False, 'evidence_valid': evidence_valid,
              'observed_product_gates': {'geometry': False, 'transparency': False, 'animation': False},
              'scope': 'Declared Java-style geometry and independent body/rear contribution; no native RGB comparison'}
    if not evidence_valid:
        return output
    images = {label: rgb(row['path']) for label, row in source['captures'].items()}
    size = next(iter(sizes))
    for label, row in source['rows'].items():
        if row['control'] != 'wet':
            continue
        dry_label = label[:-3] + 'dry'
        expected = expected_mask(row, source, size)
        selected = np.asarray(Image.fromarray((expected * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(17))) > 0
        if row['route'] != 'editor':
            selected[size[1] // 2 - 6:size[1] // 2 + 6, size[0] // 2 - 6:size[0] // 2 + 6] = False
            expected &= selected
        if dry_label in images:
            actual = difference_mask(images[label], images[dry_label], selected, LIMITS['rgb_delta'])
            if not row['case'].startswith('wet_'):
                output['geometry'][label] = product_geometry(actual, expected)
        later = label + '_later'
        if later in images and not source['frozen']:
            interior = np.asarray(Image.fromarray((expected * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5))) > 0
            output['animation'][label] = contribution(images[label], images[later], interior, LIMITS['temporal_delta'])
        if row['case'] != 'wet_oak_fence':
            continue
        required = {name: label[:-3] + name for name in ('dry', 'liquid_only', 'water_only', 'rearless', 'empty')}
        if not all(value in images for value in required.values()):
            continue
        water = difference_mask(images[required['water_only']], images[required['empty']], selected, LIMITS['rgb_delta'])
        regions = {
            'body': ((3.43, 3.18, 4.), (3.57, 3.18, 4.), (3.57, 3.50, 4.), (3.43, 3.50, 4.)),
            'rear': ((3.10, 3.35, 4.), (3.28, 3.35, 4.), (3.28, 3.55, 4.), (3.10, 3.55, 4.)),
        }
        result = output['transparency'][label] = {'water_pixels': int(water.sum()), 'regions': {}}
        for name, points in regions.items():
            region = region_mask(row, source, size, points)
            underlying = difference_mask(images[required['dry']], images[required['empty']], region, LIMITS['rgb_delta'])
            eligible = region & water & underlying
            control = 'liquid_only' if name == 'body' else 'rearless'
            result['regions'][name] = contribution(images[label], images[required[control]], eligible)
            result['regions'][name]['underlying_control_pixels'] = int(underlying.sum())
        result['passed'] = (result['water_pixels'] >= LIMITS['minimum_water_pixels']
                            and all(value['passed'] for value in result['regions'].values()))
    output['observed_product_gates'] = {
        'geometry': bool(output['geometry']) and all(row['passed'] for row in output['geometry'].values()),
        'transparency': bool(output['transparency']) and all(row['passed'] for row in output['transparency'].values()),
        'animation': bool(output['animation']) and all(row['passed'] for row in output['animation'].values()),
    }
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis')
    result = analyze(args.source)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps(result['observed_product_gates']))


if __name__ == '__main__':
    main()
