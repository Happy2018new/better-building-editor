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
from projection import block_registry
from projection.cell import decode, foreground

LIMITS = {'rgb_delta': 8, 'minimum_water_pixels': 24, 'minimum_mask_iou': .80,
          'maximum_boundary_pixels': 6, 'minimum_contribution_pixels': 8,
          'minimum_contribution_fraction': .10, 'temporal_delta': 2}
TRANSPARENCY_REGIONS = {
    'body': ((3.43, 3.18, 4.), (3.57, 3.18, 4.), (3.57, 3.50, 4.), (3.43, 3.50, 4.)),
    'rear': ((3.10, 3.35, 4.), (3.28, 3.35, 4.), (3.28, 3.55, 4.), (3.10, 3.55, 4.)),
}
PARTIAL_BODY_REGIONS = {
    'body': ((3.18, 3.50, 3.25), (3.35, 3.50, 3.25),
             (3.35, 3.50, 3.65), (3.18, 3.50, 3.65)),
    'rear': ((3.10, 3.67, 4.), (3.28, 3.67, 4.),
             (3.28, 3.78, 4.), (3.10, 3.78, 4.)),
}
FACE_INDICES = ((4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
                (3, 0, 4, 7), (1, 2, 6, 5), (3, 2, 1, 0))
_NATIVE_WORLD_GEOMETRY = object()
_NATIVE_EDITOR_GUI = object()


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


def recorded_editor_gui(state):
    """Use the captured SDK integer and cache agreement, never an image fit."""
    if not isinstance(state, dict):
        raise ValueError('Captured editor state is missing')
    cache = state.get('gui_cache')
    if not isinstance(cache, dict):
        raise ValueError('Captured editor SDK GUI cache is missing')
    gui = cache.get('sdk_integer_gui')
    cached = cache.get('cached_gui')
    if (isinstance(gui, bool) or not isinstance(gui, (int, float))
            or not 1. <= gui < float('inf') or gui != round(gui)
            or isinstance(cached, bool) or not isinstance(cached, (int, float)) or cached != gui):
        raise ValueError('Captured editor SDK GUI scale is invalid or differs from its cache')
    return float(gui)


def bind_native_editor_gui(source):
    """Opt in per parsed report; raw JSON fields cannot select this oracle."""
    states = []
    for collection in (source['rows'], source.get('extra_rows', {})):
        states.extend(row['ready'] for label, row in collection.items()
                      if label.startswith('editor_'))
    for label, holdout in source.get('alpha_controls', {}).items():
        if label.startswith('editor_'):
            states.append(holdout['baseline'])
            states.extend(phase['ready'] for phase in holdout['phases'].values())
    states.extend(burst['row']['ready'] for burst in source.get('flow_bursts', {}).values()
                  if burst['row']['route'] == 'editor')
    guis = sorted(set(recorded_editor_gui(state) for state in states))
    source[_NATIVE_EDITOR_GUI] = True
    return {'kind': 'captured_sdk_integer_gui_anchor', 'states_verified': len(states),
            'native_gui_scales': guis, 'image_fit_or_roi_search': False,
            'legacy_default_gui': 4.}


def scene_project(points, shape, state, native_gui=4.):
    if (isinstance(native_gui, bool) or not isinstance(native_gui, (int, float))
            or not 1. <= native_gui < float('inf') or native_gui != round(native_gui)):
        raise ValueError('Editor projection needs a positive integer native GUI scale')
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
    center = (position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / float(native_gui))
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
        if source.get(_NATIVE_EDITOR_GUI) is True:
            points = scene_project(points, shape, row['ready'], native_gui=recorded_editor_gui(row['ready']))
        else:
            points = scene_project(points, shape, row['ready'])
        engine = row['ready']['screen_size']
        return [(point[0] * size[0] / engine[0], point[1] * size[1] / engine[1]) for point in points]
    camera = row['camera']
    origin = row['ready']['origin']
    points = [tuple(point[i] + origin[i] for i in range(3)) for point in points]
    if source.get(_NATIVE_WORLD_GEOMETRY) is not None:
        from water_native_projection import stone_project
        return stone_project(points, camera, size, source[_NATIVE_WORLD_GEOMETRY])
    projected = project_points(points, camera['position'], camera['target'], size,
                               source['camera_calibration']['vertical_fov'])
    return [(point['screenX'], point['screenY']) for point in projected]


def expected_mask(row, source, size):
    if (row['case'].startswith('neighbor_') or
            (source.get(_NATIVE_WORLD_GEOMETRY) is not None and row['route'] != 'editor'
             and row['case'] == 'falling')):
        return unoccluded_neighbor_mask(row, source, size)
    image = Image.new('L', size)
    draw = ImageDraw.Draw(image)
    for shape, polygon in water_polygons(row['ready']['shapes']):
        draw.polygon(project(polygon, shape, row, source, size), fill=255)
    return np.asarray(image) > 0


def fixture_solid_boxes(row):
    """Opaque geometry in the fixed public neighbor controls, not a block parser."""
    for position, encoded in row['source']['cells']:
        material = foreground(decode(encoded))
        name = material[0]
        if name in ('minecraft:stone', 'minecraft:gold_block'):
            local = ((0., 0., 0., 1., 1., 1.),)
        elif name == 'minecraft:oak_slab':
            states = block_registry.states(material)
            if states.get('minecraft:vertical_half', states.get('vertical_half')) not in ('bottom', None):
                raise ValueError('Neighbor oracle requires the public bottom slab')
            local = ((0., 0., 0., 1., .5, 1.),)
        elif name == 'minecraft:oak_stairs':
            states = block_registry.states(material)
            if states.get('weirdo_direction') != 0 or states.get('upside_down_bit') is not False:
                raise ValueError('Neighbor oracle requires the public upright east stair')
            local = ((0., 0., 0., 1., .5, 1.), (.5, .5, 0., 1., 1., 1.))
        else:
            continue
        for box in local:
            yield tuple(box[axis] + position[axis % 3] for axis in range(6))


def raster_depth(buffer, points, depths, perspective):
    for indices in ((0, 1, 2), (0, 2, 3)):
        triangle = np.asarray([points[index] for index in indices])
        if not np.isfinite(triangle).all():
            raise ValueError('Neighbor triangle lies outside the projectable camera')
        left, top = np.floor(triangle.min(axis=0)).astype(int)
        right, bottom = np.ceil(triangle.max(axis=0)).astype(int)
        left, right = max(0, left), min(buffer.shape[1] - 1, right)
        top, bottom = max(0, top), min(buffer.shape[0] - 1, bottom)
        if left > right or top > bottom:
            continue
        a, b, c = triangle
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-9:
            continue
        x, y = np.meshgrid(np.arange(left, right + 1) + .5, np.arange(top, bottom + 1) + .5)
        first = ((b[1] - c[1]) * (x - c[0]) + (c[0] - b[0]) * (y - c[1])) / denominator
        second = ((c[1] - a[1]) * (x - c[0]) + (a[0] - c[0]) * (y - c[1])) / denominator
        third = 1. - first - second
        inside = (first >= -1e-7) & (second >= -1e-7) & (third >= -1e-7)
        z = np.asarray([depths[index] for index in indices])
        depth = (1. / (first / z[0] + second / z[1] + third / z[2]) if perspective
                 else first * z[0] + second * z[1] + third * z[2])
        selected = buffer[top:bottom + 1, left:right + 1]
        np.minimum(selected, np.where(inside, depth, np.inf), out=selected)


def unoccluded_neighbor_mask(row, source, size):
    """Independent depth rasterization keeps opaque neighbors in front of water."""
    water = np.full((size[1], size[0]), np.inf)
    solid = np.full_like(water, np.inf)
    world = row['route'] != 'editor'
    if world:
        camera = row['camera']
        eye = np.asarray(camera['position']) - np.asarray(row['ready']['origin'])
        direction = np.asarray(camera['target']) - np.asarray(camera['position'])
        direction /= np.linalg.norm(direction)
    else:
        eye = np.zeros(3)
        direction = -np.asarray(OrbitCamera(*row['ready']['camera_pose']).basis()[2])

    def draw(buffer, polygon, shape):
        depths = [float(np.dot(np.asarray(point) - eye, direction)) for point in polygon]
        raster_depth(buffer, project(polygon, shape, row, source, size), depths, world)

    shapes = row['ready']['shapes']
    for shape, polygon in water_polygons(shapes):
        draw(water, polygon, shape)
    for x0, y0, z0, x1, y1, z1 in fixture_solid_boxes(row):
        corners = ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1),
                   (x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1))
        for face in FACE_INDICES:
            draw(solid, [corners[index] for index in face], shapes[0])
    return np.isfinite(water) & (water <= solid + 1e-5)


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


def fixed_alpha_regions(images, regions):
    """Reject opaque or animated controls using one frozen water geometry."""
    clear, opaque = images['0'].astype(np.float64), images['1'].astype(np.float64)
    result = {}
    for name, selected in regions.items():
        eligible = difference_mask(clear, opaque, selected, LIMITS['rgb_delta'])
        count = int(eligible.sum())
        row = {'eligible_pixels': count, 'phases': {}, 'passed': False}
        if count >= LIMITS['minimum_contribution_pixels']:
            for label, alpha in (('0_25', .25), ('0_45', .45), ('0_75', .75)):
                actual = images[label].astype(np.float64)
                expected = clear * (1. - alpha) + opaque * alpha
                rms = float(np.sqrt(np.mean((actual[eligible] - expected[eligible]) ** 2)))
                body = difference_mask(actual, opaque, eligible, 3)
                water = difference_mask(actual, clear, eligible, 3)
                row['phases'][label] = {'alpha': alpha, 'endpoint_rgb_rmse': rms,
                    'body_pixels': int(body.sum()), 'water_pixels': int(water.sum()),
                    'passed': bool(rms <= 3. and body.sum() >= count * .8 and water.sum() >= count * .8)}
            default_rms = float(np.sqrt(np.mean((images['default'][eligible].astype(np.float64)
                                               - images['0_45'][eligible]) ** 2)))
            row['default_rgb_rmse'] = default_rms
            row['passed'] = default_rms <= 3. and all(phase['passed'] for phase in row['phases'].values())
        result[name] = row
    return {'regions': result, 'passed': bool(result) and all(row['passed'] for row in result.values())}


def analyze(path, native_world_geometry=False, native_editor_gui=False):
    source = json.loads(path.read_bytes())
    failures = capture_failures(source['captures'], source['session_binding'])
    oracle = None
    editor_oracle = None
    if native_editor_gui:
        try:
            editor_oracle = bind_native_editor_gui(source)
        except (ValueError, KeyError, TypeError) as exc:
            failures.append({'native_editor_gui': str(exc)})
    if native_world_geometry:
        try:
            from water_native_projection import stone_camera_model
            import water_native_projection
            if not any(route in ('full', 'missing') for route in source.get('routes', ())):
                raise ValueError('Native world geometry requires a world route')
            reference = source['camera_calibration']
            calibration_path = Path(reference['path'])
            if hashlib.sha256(calibration_path.read_bytes()).hexdigest() != reference['sha256']:
                raise ValueError('Native world geometry calibration bytes changed')
            model = stone_camera_model(json.loads(calibration_path.read_bytes()),
                source['session_binding'], source['source_contract_sha256'])
            source[_NATIVE_WORLD_GEOMETRY] = model
            oracle = {'kind': 'native_stone_camera_with_opaque_support_depth',
                'calibration_sha256': reference['sha256'], 'model': model,
                'helper_sha256': hashlib.sha256(Path(water_native_projection.__file__).read_bytes()).hexdigest()}
        except (OSError, ValueError, KeyError, TypeError) as exc:
            failures.append({'native_world_geometry': str(exc)})
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
                if source.get('alpha_controls_requested') and control == 'wet' and case.startswith('wet_'):
                    holdout = source.get('alpha_controls', {}).get(label, {})
                    phases = holdout.get('phases', {})
                    if any(name not in phases or phases[name].get('capture_label') not in source['captures']
                           for name in ('0', '0_25', '0_45', '0_75', '1', 'default')):
                        failures.append({'missing_requested_alpha_control': label})
    evidence_valid = (not failures and source['completed'] is True and source['restored'] is True
                      and not source['cleanup_errors'])
    output = {'schema': 1, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'limits': LIMITS,
              'completed': source['completed'], 'restored': source['restored'], 'cleanup_errors': source['cleanup_errors'],
              'capture_failures': failures, 'captures_verified': not failures, 'geometry': {}, 'transparency': {},
              'animation': {}, 'alpha_controls': {}, 'transparency_phase_controlled': source.get('frozen') is True,
              'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
              'product_style_accepted': False, 'evidence_valid': evidence_valid,
              'observed_product_gates': {'geometry': False, 'transparency': False, 'animation': False},
              'scope': 'Declared Java-style geometry and independent body/rear contribution; no native RGB comparison'}
    if native_world_geometry:
        output['geometry_oracle'] = oracle
    if native_editor_gui:
        output['editor_geometry_oracle'] = editor_oracle
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
        holdout = source.get('alpha_controls', {}).get(label)
        if holdout:
            from analyze_liquid_transparency import alpha_context
            phase_labels = ('0', '0_25', '0_45', '0_75', '1', 'default')
            phases = holdout.get('phases', {})
            complete = all(name in phases and phases[name].get('capture_label') in images for name in phase_labels)
            alpha_result = output['alpha_controls'][label] = {'complete': complete, 'passed': False}
            if complete:
                context = alpha_context(holdout['baseline'], row['route'] != 'editor')
                unchanged = all(alpha_context(phases[name]['ready'], row['route'] != 'editor') == context
                                for name in phase_labels)
                measured = fixed_alpha_regions(
                    {name: images[phases[name]['capture_label']] for name in phase_labels},
                    {name: region_mask(row, source, size, points) for name, points in
                     (PARTIAL_BODY_REGIONS if row['case'] in ('wet_oak_slab', 'wet_oak_stairs')
                      else TRANSPARENCY_REGIONS).items()})
                alpha_result.update(measured, geometry_unchanged=unchanged)
                alpha_result['passed'] = measured['passed'] and unchanged and source.get('frozen') is True
        if row['case'] != 'wet_oak_fence':
            continue
        required = {name: label[:-3] + name for name in ('dry', 'liquid_only', 'water_only', 'rearless', 'empty')}
        if not all(value in images for value in required.values()):
            continue
        water = difference_mask(images[required['water_only']], images[required['empty']], selected, LIMITS['rgb_delta'])
        result = output['transparency'][label] = {'water_pixels': int(water.sum()), 'regions': {},
                                                 'phase_controlled': source.get('frozen') is True}
        for name, points in TRANSPARENCY_REGIONS.items():
            region = region_mask(row, source, size, points)
            underlying = difference_mask(images[required['dry']], images[required['empty']], region, LIMITS['rgb_delta'])
            eligible = region & water & underlying
            control = 'liquid_only' if name == 'body' else 'rearless'
            result['regions'][name] = contribution(images[label], images[required[control]], eligible)
            result['regions'][name]['underlying_control_pixels'] = int(underlying.sum())
        result['passed'] = (result['phase_controlled'] and result['water_pixels'] >= LIMITS['minimum_water_pixels']
                            and all(value['passed'] for value in result['regions'].values()))
        if holdout:
            result['passed'] = result['passed'] and output['alpha_controls'][label]['passed']
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
    parser.add_argument('--native-world-geometry', action='store_true',
                        help='Use independently calibrated native stone coordinates and opaque falling supports')
    parser.add_argument('--native-editor-gui', action='store_true',
                        help='Use captured SDK integer GUI/cache agreement; default retains legacy GUI4 coordinates')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis')
    result = analyze(args.source, native_world_geometry=args.native_world_geometry,
                     native_editor_gui=args.native_editor_gui)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='ascii')
    print(json.dumps(result['observed_product_gates']))


if __name__ == '__main__':
    main()
