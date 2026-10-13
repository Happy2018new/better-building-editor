"""Score declared item body and animated fallback highlight from paired pixels.

This diagnostic never changes production qualification. Full pose/depth/opacity
acceptance and unsupported item families remain separate work.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from camera_projection import project_points
from generate_flat_item_proxies import source_path
from item_sprite_capture_contract import (camera_matches, paired_layout_matches,
                                          scene_layout, snapshot_digest, snapshot_sources)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.camera import OrbitCamera
from projection import block_registry
from projection.cell import actor_data, foreground
from projection.debug_blueprints import build
from projection.debug_item_blueprints import IDENTITY, PAIRS
from projection.nbt_spatial import root_payload, scalar
from projection.visible_actor import entity_nbt

LIMITS = {'rgb_delta': 8, 'temporal_delta': 2, 'minimum_body_pixels': 8,
          'minimum_body_iou': .70, 'maximum_boundary_pixels': 4,
          'minimum_motion_pixels': 4, 'minimum_motion_fraction': .04,
          'maximum_control_motion_pixels': 3, 'maximum_escape_fraction': .05}


def item_polygons(position, texture, pose, rotation=0., facing=2):
    """Project opaque source bitmap pixels at the declared frame support plane."""
    alpha = np.asarray(texture.convert('RGBA'))[:, :, 3]
    size, z = pose['size_pixels']/16., pose['front_z_pixels']/16.-.5
    sine, cosine = math.sin(math.radians(rotation)), math.cos(math.radians(rotation))
    def point(u, v):
        x, y = (u/texture.width-.5)*size, (.5-v/texture.height)*size
        x, y = x*cosine-y*sine, x*sine+y*cosine
        if facing == 0:
            local = (-x, z, -y)
        elif facing == 1:
            local = (-x, -z, y)
        elif facing == 2:
            local = (-x, y, z)
        elif facing == 3:
            local = (x, y, -z)
        elif facing == 4:
            local = (z, y, x)
        elif facing == 5:
            local = (-z, y, -x)
        else:
            raise ValueError('Item face must be one of the six block faces')
        return tuple(position[i]+.5+local[i] for i in range(3))
    for y, x in np.argwhere(alpha >= 128):
        yield tuple(point(u, v) for u, v in ((x, y), (x+1, y), (x+1, y+1), (x, y+1)))


def project_editor(points, position, state, size):
    groups = {row['key']: row for row in state['groups_data']}
    controls = [row for row in state['banks'] if row['key'] in groups and any(row['visible'])]
    if not controls:
        raise ValueError('Expected item has no visible actual native control')
    # Empty-frame negative controls have no sprite owner of their own. The
    # affine camera can extrapolate them from the nearest actual item control.
    row = min(controls, key=lambda row: sum((groups[row['key']]['origin'][i]-position[i])**2
                                           for i in range(3)))
    origin = groups[row['key']]['origin']
    slot = row['front']
    actual_position, actual_size = row['doll_positions'][slot], row['doll_sizes'][slot]
    unit = row['poses'][slot][0]*min(actual_size)
    center = (actual_position[0]+actual_size[0]/2.,
              actual_position[1]+actual_size[1]/2.-min(actual_size)/4.)
    right, up, unused = OrbitCamera(*state['camera_pose']).basis()
    result = []
    for point in points:
        offset = tuple(point[i]-origin[i]-2. for i in range(3))
        result.append(((center[0]+unit*sum(offset[i]*right[i] for i in range(3)))*size[0]/state['screen_size'][0],
                       (center[1]-unit*sum(offset[i]*up[i] for i in range(3)))*size[1]/state['screen_size'][1]))
    return result


def expected_mask(position, row, texture, pose, size, calibration=None, facing=2, rotation=0.):
    mask = Image.new('L', size)
    draw = ImageDraw.Draw(mask)
    for polygon in item_polygons(position, texture, pose, rotation, facing):
        if row['label'].startswith('editor_'):
            points = project_editor(polygon, position, row['state'], size)
        else:
            camera = row['camera_expected']
            polygon = [tuple(point[i]+row['state']['origin'][i] for i in range(3)) for point in polygon]
            points = project_points(polygon, camera['position'], camera['target'], size,
                                    calibration['vertical_fov'])
            points = [(point['screenX'], point['screenY']) for point in points]
        draw.polygon(points, fill=255)
    return np.asarray(mask) > 0


def expanded(mask, pixels=9):
    return np.asarray(Image.fromarray((mask*255).astype(np.uint8)).filter(ImageFilter.MaxFilter(pixels))) > 0


def body_measurement(positive, hidden, expected):
    actual = difference_mask(positive, hidden, expanded(expected), LIMITS['rgb_delta'])
    union = int(np.count_nonzero(actual | expected))
    observed, declared = mask_row(actual), mask_row(expected)
    iou = int(np.count_nonzero(actual & expected))/max(1, union)
    edge = (max(abs(a-b) for a, b in zip(observed['bounds'], declared['bounds']))
            if observed['bounds'] and declared['bounds'] else None)
    return {'observed': observed, 'declared': declared, 'iou': iou,
            'maximum_boundary_pixels': edge, 'passed': bool(
                observed['pixels'] >= LIMITS['minimum_body_pixels'] and iou >= LIMITS['minimum_body_iou']
                and edge is not None and edge <= LIMITS['maximum_boundary_pixels'])}


def temporal_measurement(images, expected, enchanted):
    selected = expanded(expected, 3)
    ys, xs = np.nonzero(expanded(expected))
    envelope = np.zeros_like(expected)
    if len(xs):
        envelope[ys.min():ys.max()+1, xs.min():xs.max()+1] = True
    changed = np.zeros_like(expected)
    for image in images[1:]:
        changed |= difference_mask(images[0], image, envelope, LIMITS['temporal_delta'])
    inside, escaped = int(np.count_nonzero(changed & selected)), int(np.count_nonzero(changed & ~selected))
    total = int(np.count_nonzero(expected))
    passed = (inside >= LIMITS['minimum_motion_pixels'] and inside/max(1, total) >= LIMITS['minimum_motion_fraction']
              and escaped/max(1, inside+escaped) <= LIMITS['maximum_escape_fraction']) if enchanted else (
                  inside+escaped <= LIMITS['maximum_control_motion_pixels'])
    return {'eligible_pixels': total, 'inside_pixels': inside, 'escaped_pixels': escaped,
            'fraction': inside/max(1, total), 'enchanted': enchanted, 'passed': bool(passed)}


def calibration_matches(control, camera, size, binding):
    if not isinstance(control, dict) or not isinstance(control.get('data'), dict):
        return False
    path = Path(control.get('path', ''))
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != control.get('sha256'):
        return False
    data = control['data']
    if json.loads(path.read_bytes()) != data:
        return False
    if (data.get('passed') is not True or data.get('completed') is not True or data.get('restored') is not True
            or data.get('fixture_identity') != 'camera.calibration.stone'
            or data.get('cleanup_errors') or data.get('capture_size') != list(size)
            or data.get('engine_screen') != camera['screen'] or data.get('reported_fov') != camera['fov']
            or type(data.get('vertical_fov')) not in (float, int)
            or not math.isfinite(data['vertical_fov']) or not 0 < data['vertical_fov'] < 180):
        return False
    if any(data.get('session', {}).get(key) != binding.get(key)
           for key in ('owner', 'game_pid', 'game_identity', 'session_file')):
        return False
    views = data.get('views')
    if not isinstance(views, list) or len(views) != 3 or {row.get('view') for row in views} != {'front', 'right', 'tilted'}:
        return False
    captures = {}
    for row in views:
        fit = row.get('fit', {})
        if (row.get('passed') is not True or fit.get('boundary_rms_pixels', math.inf) > 2
                or fit.get('mask_iou', 0) < .95 or fit.get('outline_recall_2px', 0) < .985
                or fit.get('outline_precision_2px', 0) < .985):
            return False
        if row.get('camera', {}).get('screen') != camera['screen'] or row.get('camera', {}).get('fov') != camera['fov']:
            return False
        for mode in ('shown', 'hidden'):
            capture = row.get(mode)
            if not isinstance(capture, dict) or (capture.get('width'), capture.get('height')) != size:
                return False
            captures[row['view']+'_'+mode] = capture
    return not capture_failures(captures, data.get('session', {}))


def analyze(path):
    source = json.loads(path.read_bytes())
    rows = {row['label']: row for row in source.get('captures', ())}
    captures = {label: row['capture'] for label, row in rows.items()}
    binding = source.get('session', {})
    failures = capture_failures(captures, binding)
    inputs = source.get('launch_inputs')
    if (not inputs or source.get('source_unchanged') is not True or inputs != source.get('inputs_after')
            or snapshot_digest(inputs) != source.get('launch_inputs_sha256')):
        failures.append('Source/resource launch snapshot was missing or changed')
    if source.get('schema') != 2 or source.get('fixture') != 'test.entities.item_contents':
        failures.append('Public item fixture capture schema does not match this analyzer')
    sizes = {(row.get('width'), row.get('height')) for row in captures.values()}
    if len(sizes) != 1:
        failures.append('Capture dimensions changed or were absent')
    for label, row in rows.items():
        if label.startswith('editor_'):
            before, after = scene_layout(row.get('state')), scene_layout(row.get('state_after'))
            if before is None or before != after:
                failures.append({'scene_layout_drift': label})
        elif label.startswith('world_'):
            expected = row.get('camera_expected')
            if not all(camera_matches(row.get(key), expected) for key in ('camera_before', 'camera_after')):
                failures.append({'world_camera_drift': label})
    result = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': LIMITS, 'capture_failures': failures, 'captures_verified': not failures,
              'evidence_valid': not failures and source.get('completed') is True and not source.get('cleanup_errors'),
              'body': {}, 'temporal': {}, 'observed_product_gates': {},
              'requested_routes': ['editor', 'full'] if source.get('world_requested') else ['editor'],
              'production_qualified': False, 'native_glint_accepted': False,
              'native_shader_errors': source.get('native_shader_errors', []),
              'pending': ['all six faces and eight rotations', 'depth and opacity', 'item replacement',
                          'unsupported item families and shelf slots'],
              'scope': 'Declared diamond-sword silhouette and moving analytic highlight; not vanilla glint parity'}
    if not result['evidence_valid']:
        return result
    if snapshot_sources(ROOT) != inputs:
        failures.append('Replay source/resource files differ from the frozen capture inputs')
        result['evidence_valid'] = result['captures_verified'] = False
        return result
    spec_path = source_path()
    if inputs.get(spec_path.relative_to(ROOT).as_posix()) != hashlib.sha256(spec_path.read_bytes()).hexdigest():
        failures.append('Versioned item pose/source does not match frozen launch')
        result['evidence_valid'] = result['captures_verified'] = False
        return result
    spec = json.loads(spec_path.read_bytes())
    item = next(row for row in spec['items'] if row['identifier'] == 'minecraft:diamond_sword' and row['aux'] == 0)
    texture_path = ROOT/item['generated_texture']
    if inputs.get(item['generated_texture']) != item['texture_sha256'] or hashlib.sha256(texture_path.read_bytes()).hexdigest() != item['texture_sha256']:
        failures.append('Versioned item bitmap does not match frozen launch')
        result['evidence_valid'] = result['captures_verified'] = False
        return result
    images = {label: rgb(row['path']) for label, row in captures.items()}
    size = next(iter(sizes))
    document = build(IDENTITY)
    with Image.open(texture_path) as texture:
        for route, prefix in (('editor', 'editor_temporal_'), ('full', 'world_full_')):
            temporal_labels = [prefix+str(index) for index in range(3)]
            hidden_label = 'editor_items_hidden' if route == 'editor' else 'world_full_items_hidden'
            required = temporal_labels+[hidden_label]
            if not all(label in rows for label in required):
                result['observed_product_gates'][route] = {'body': False, 'animation': False, 'status': 'NOT_TESTED'}
                continue
            first = rows[temporal_labels[0]]
            calibration = None
            if route == 'editor':
                if not all(paired_layout_matches(first['state'], rows[label]['state']) for label in required):
                    failures.append('Editor body/temporal controls have different native layouts')
                    continue
                hidden_banks = rows[hidden_label]['state']['banks']
                if not hidden_banks or any(any(bank['visible']) for bank in hidden_banks):
                    failures.append('Editor negative control did not hide the owned item surfaces')
                    continue
            else:
                if not all(camera_matches(rows[label]['camera_expected'], first['camera_expected'])
                           and rows[label]['state'].get('origin') == first['state'].get('origin')
                           for label in required):
                    failures.append('World body/temporal controls have different cameras or origins')
                    continue
                calibration = source.get('camera_calibration', {}).get('data')
                camera = first['camera_expected']
                if not calibration_matches(source.get('camera_calibration'), camera, size, binding):
                    result['observed_product_gates'][route] = {'body': False, 'animation': False,
                        'status': 'NOT_TESTED', 'reason': 'Independent camera calibration missing or inconsistent'}
                    continue
                hidden_groups = rows[hidden_label]['state'].get('groups_data')
                if not hidden_groups or any(group['visible'] for group in hidden_groups):
                    failures.append('World negative control did not hide the owned item models')
                    continue
            for pair in PAIRS:
                for mode in ('plain', 'enchanted', 'empty'):
                    position = pair[mode]
                    cell = document.get(position)
                    facing = block_registry.states(foreground(cell))['facing_direction']
                    rotation = scalar(root_payload(entity_nbt(actor_data(cell))), 'ItemRotation')
                    expected = expected_mask(position, first, texture, spec['frame_pose'], size,
                                             calibration, facing, rotation)
                    key = route+'_'+pair['id']+'_'+mode
                    sequence = [images[label] for label in temporal_labels]
                    if mode != 'empty':
                        result['body'][key] = body_measurement(sequence[0], images[hidden_label], expected)
                    else:
                        delta = difference_mask(sequence[0], images[hidden_label], expanded(expected), LIMITS['rgb_delta'])
                        result['body'][key] = {'unexpected_pixels': int(delta.sum()),
                            'passed': int(delta.sum()) <= LIMITS['maximum_control_motion_pixels']}
                    result['temporal'][key] = temporal_measurement(sequence, expected, mode == 'enchanted')
            result['observed_product_gates'][route] = {
                'body': all(row['passed'] for key, row in result['body'].items() if key.startswith(route+'_')),
                'animation': all(row['passed'] for key, row in result['temporal'].items() if key.startswith(route+'_')),
                'status': 'SCORED'}
    result['capture_failures'] = failures
    result['captures_verified'] = result['evidence_valid'] = not failures
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis')
    result = analyze(args.source)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True)+'\n', encoding='ascii')
    print(json.dumps(result['observed_product_gates']))
    return 0 if result['evidence_valid'] and all(
        result['observed_product_gates'].get(route, {}).get('status') == 'SCORED'
        and result['observed_product_gates'][route]['body']
        and result['observed_product_gates'][route]['animation']
        for route in result['requested_routes']) and not result['native_shader_errors'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
