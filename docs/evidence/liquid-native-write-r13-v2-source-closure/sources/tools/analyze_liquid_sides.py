"""Offline, source-driven liquid side invariants; no SDK or native operations."""
import argparse
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from analyze_liquid_workspace import capture_failures, difference_mask, rgb
from camera_projection import project_points

ROOT = Path(__file__).resolve().parents[1]
SOURCE_IDS = ('water_depth_0_foreground', 'water_depth_3_foreground',
              'water_flow_corner_foreground', 'water_falling_column_foreground')
ROUTES = ('scene', 'full', 'missing', 'native')
SIDE_CORNERS = {'north': (0, 1), 'south': (2, 3), 'west': (3, 0), 'east': (1, 2)}
NORMALS = {'north': (0, 0, -1), 'south': (0, 0, 1),
           'west': (-1, 0, 0), 'east': (1, 0, 0)}
FACE_BITS = {'top': 1, 'north': 2, 'south': 4, 'west': 8, 'east': 16, 'bottom': 32}
LIMITS = {'minimum_mask_iou': .95, 'maximum_boundary_pixels': 3.,
          'minimum_low_side_pixels': 24., 'minimum_marker_contrast': 12.,
          'minimum_marker_samples': 80, 'maximum_rgb_rmse': 3.}
BOUND_FILES = ('tools/analyze_liquid_sides.py', 'tools/camera_projection.py',
               'tools/analyze_liquid_workspace.py',
               'behavior_pack/modern_projection/projection/debug_liquid_blueprints.py',
               'behavior_pack/modern_projection/projection/debug_blueprints.py',
               'behavior_pack/modern_projection/projection/block_registry_data.py',
               'behavior_pack/modern_projection/projection/block_registry.py',
               'behavior_pack/modern_projection/projection/cell.py',
               'behavior_pack/modern_projection/projection/model.py')


def fingerprint(path):
    path = Path(path).resolve(strict=True)
    return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def read_reference(reference):
    path = Path(reference['path'])
    if not path.is_absolute() or fingerprint(path)['sha256'] != reference['sha256']:
        raise ValueError('Changed or non-absolute reference: ' + str(path))
    return path


def source_bindings():
    return {name: fingerprint(ROOT / name) for name in BOUND_FILES}


def _builtin_document(identity, control):
    if identity not in SOURCE_IDS:
        raise ValueError('Undeclared built-in liquid source: ' + identity)
    source_path = str(ROOT / 'behavior_pack/modern_projection')
    if source_path not in sys.path:
        sys.path.insert(0, source_path)
    from projection.debug_liquid_blueprints import source_document
    return source_document(identity, isolated=True, control=control)


def builtin_geometry(identity, control='supported_positive'):
    """Independent rational corner table for the four declared pure-water sources."""
    document = _builtin_document(identity, control)
    from projection.block_registry import states
    from projection.cell import encode, foreground, background
    cells, liquids, blockers = [], {}, set()
    for position, cell in sorted(document.blocks.items()):
        cells.append([list(position), encode(cell)])
        for layer, value in enumerate((foreground(cell), background(cell))):
            if value[0] in ('minecraft:water', 'minecraft:flowing_water'):
                liquids[position] = (states(value)['liquid_depth'], layer)
            elif value[0] == 'minecraft:stone':
                blockers.add(position)
            elif value[0] != 'minecraft:air':
                raise ValueError('Pure-source geometry has an undeclared blocker')
    corners, surfaces = ((0, 0), (1, 0), (1, 1), (0, 1)), []
    offsets = ((0, 1, 0), (0, 0, -1), (0, 0, 1),
               (-1, 0, 0), (1, 0, 0), (0, -1, 0))
    for position, (_, layer) in sorted(liquids.items()):
        heights = []
        for cx, cz in corners:
            neighbors = [(position[0] + dx, position[1], position[2] + dz)
                         for dx, dz in ((cx-1, cz-1), (cx, cz-1), (cx, cz), (cx-1, cz))]
            heights.append(_corner_height(neighbors, liquids, blockers))
        faces = sum(1 << face for face, delta in enumerate(offsets)
                    if tuple(position[i]+delta[i] for i in range(3)) not in liquids
                    and tuple(position[i]+delta[i] for i in range(3)) not in blockers)
        surfaces.append({'position': list(position), 'layer': layer,
                         'heights': [int(height * 255 + Fraction(1, 2)) for height in heights],
                         'faces': faces})
    return {'source_id': identity, 'control': control, 'size': list(document.size),
            'source_cells': cells, 'surfaces': surfaces,
            'native_readback_cells': [[list(pos), encode(document.get(pos))] for pos in sorted(
                {tuple(pos[i]+delta[i] for i in range(3)) for pos in document.blocks
                 for delta in ((x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1))})],
            'geometry_basis': 'Independent rational four-cell rule; diagnostic, not native acceptance'}


def _corner_height(neighbors, liquids, blockers):
    if any((pos[0], pos[1]+1, pos[2]) in liquids for pos in neighbors):
        return Fraction(1)
    amount, weight = Fraction(0), 0
    for position in neighbors:
        if position in liquids:
            depth = liquids[position][0]
            multiplier = 11 if depth == 0 or depth >= 8 else 1
            amount += Fraction(8 if depth >= 8 else 8-depth, 9) * multiplier
            weight += multiplier
        elif position not in blockers:
            weight += 1
    if not weight:
        raise ValueError('Corner has no declared water contributor')
    return amount / weight


def surface_at(geometry, position, layer=0):
    rows = [row for row in geometry['surfaces']
            if row['position'] == list(position) and row['layer'] == layer]
    if len(rows) != 1:
        raise ValueError('Side does not name one built-in liquid surface')
    return rows[0]


def face_points(position, face, u, height):
    u, height = np.broadcast_arrays(np.asarray(u, float), np.asarray(height, float))
    if face == 'north':
        local = (u, height, np.zeros_like(u))
    elif face == 'south':
        local = (1-u, height, np.ones_like(u))
    elif face == 'west':
        local = (np.zeros_like(u), height, 1-u)
    elif face == 'east':
        local = (np.ones_like(u), height, u)
    else:
        raise ValueError('Unknown side: ' + face)
    return np.stack(local, axis=-1) + np.asarray(position, float)


def edge_heights(surface, face, u):
    first, last = SIDE_CORNERS[face]
    return (surface['heights'][first] * (1-np.asarray(u))
            + surface['heights'][last] * np.asarray(u)) / 255.


def project(points, projection):
    points = np.asarray(points, float)
    if not np.isfinite(points).all():
        raise ValueError('Non-finite physical point')
    shape = points.shape[:-1]
    points = points.reshape(-1, 3) + np.asarray(projection.get('origin', [0, 0, 0]), float)
    if projection['kind'] == 'affine':
        matrix = np.asarray(projection['affine'], float)
        if matrix.shape != (2, 4) or not np.isfinite(matrix).all():
            raise ValueError('Affine projection requires two finite 4-coefficient rows')
        result = np.column_stack((points, np.ones(len(points)))) @ matrix.T
    elif projection['kind'] == 'perspective':
        rows = project_points(points, projection['position'], projection['target'],
                              projection['screen'], projection['vertical_fov'], projection.get('roll', 0))
        if any(row['depth'] <= .05 for row in rows):
            raise ValueError('Declared side reaches the near plane')
        result = np.asarray([[row['screenX'], row['screenY']] for row in rows])
    else:
        raise ValueError('Unsupported projection kind')
    scale = np.asarray(projection['native_image_screen'], float) / np.asarray(projection['screen'], float)
    if not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError('Invalid full-viewport scale')
    return (result * scale).reshape(shape + (2,))


def side_preflight(declaration, side, geometry):
    surface = surface_at(geometry, side['position'], side['layer'])
    face = side['face']
    if face not in SIDE_CORNERS or not surface['faces'] & FACE_BITS[face]:
        raise ValueError('Declared side is hidden in the unchanged built-in source')
    projection = declaration['projection']
    point = np.asarray(side['position'], float) + .5 + np.asarray(projection.get('origin', [0, 0, 0]))
    toward = (np.asarray(projection['position']) - point if projection['kind'] == 'perspective'
              else np.asarray(projection['toward']))
    if np.dot(toward, NORMALS[face]) <= 0:
        raise ValueError('Declared side faces away from the frozen camera')
    u = np.asarray([.1, .5, .9])
    top = edge_heights(surface, face, u)
    bottom_xy = project(face_points(side['position'], face, u, 0), projection)
    top_xy = project(face_points(side['position'], face, u, top), projection)
    pixels = np.linalg.norm(top_xy-bottom_xy, axis=1)
    screen = np.asarray(projection['native_image_screen'])
    on_screen = bool(np.all(bottom_xy >= 0) and np.all(bottom_xy < screen)
                     and np.all(top_xy >= 0) and np.all(top_xy < screen))
    return {'position': side['position'], 'layer': side['layer'], 'face': face,
            'corner_pair': list(SIDE_CORNERS[face]), 'minimum_side_pixels': float(pixels.min()),
            'on_screen': on_screen,
            'adequate': bool(on_screen and (declaration['source_id'] != SOURCE_IDS[1]
                                           or pixels.min() >= LIMITS['minimum_low_side_pixels']))}


def validate_plan(plan):
    if plan.get('schema') != 1 or plan.get('kind') != 'liquid_side_visible_v1':
        raise ValueError('Unknown liquid side plan')
    if plan.get('limits') != LIMITS:
        raise ValueError('Side limits are fixed; no threshold relaxation or replacement')
    bindings = plan['source_bindings']
    if set(bindings) != set(BOUND_FILES):
        raise ValueError('Incomplete offline/built-in source binding')
    for name, reference in bindings.items():
        if fingerprint(ROOT/name)['sha256'] != reference['sha256']:
            raise ValueError('Offline or built-in source changed: ' + name)
        read_reference(reference)
    declarations = plan['declarations']
    ids = [row['id'] for row in declarations]
    if len(ids) != len(set(ids)) or not ids:
        raise ValueError('Nonempty unique capture declarations required')
    for name in ('crop_pairs', 'missing_pairs', 'original_pairs'):
        pair_ids = [row.get('id') for row in plan.get(name, [])]
        if (any(not isinstance(identity, str) or not identity.strip() for identity in pair_ids)
                or len(pair_ids) != len(set(pair_ids))):
            raise ValueError(name + ' require unique nonempty string IDs')
    preflight = {}
    for row in declarations:
        if row['route'] not in ROUTES or row['role'] not in ('marker', 'original', 'native_original'):
            raise ValueError('Unknown capture route or role')
        if row['role'] == 'native_original' and row['route'] != 'native':
            raise ValueError('Native reference cannot be a candidate route')
        geometry = builtin_geometry(row['source_id'], row['control'])
        if row['source_cells'] != geometry['source_cells']:
            raise ValueError('Plan cells differ from built-in exact source')
        if row['control'] == 'supported_positive' and not row['sides']:
            raise ValueError('Positive declaration lacks physical sides')
        preflight[row['id']] = [side_preflight(row, side, geometry) for side in row['sides']]
    by_id = dict(zip(ids, declarations))
    for row in declarations:
        background = row.get('background_id')
        if background:
            baseline = by_id[background]
            if (baseline['control'] != 'supported_negative' or baseline['route'] != row['route']
                    or baseline['projection'] != row['projection']
                    or baseline['source_cells'] != builtin_geometry(row['source_id'], 'supported_negative')['source_cells']):
                raise ValueError('Silhouette baseline changes support topology, projection or route')
    for pair in plan.get('crop_pairs', []):
        high, low = by_id[pair['high']], by_id[pair['low']]
        if (high['source_id'] != SOURCE_IDS[0] or low['source_id'] != SOURCE_IDS[1]
                or high['route'] != low['route'] or high['view'] != low['view']
                or high['role'] != 'marker' or low['role'] != 'marker'
                or pair['high_side'] not in high['sides'] or pair['low_side'] not in low['sides']
                or pair['high_side']['face'] != pair['low_side']['face']):
            raise ValueError('Crop pair must use declared high/low marker sides at one route/view')
    for pair in plan.get('missing_pairs', []):
        rows = [by_id[pair[key]] for key in ('baseline', 'occupied', 'restored')]
        if (any(row['route'] != 'missing' or row['source_id'] != SOURCE_IDS[2] for row in rows)
                or pair['occupied_positions'] != [[2, 3, 3]]
                or rows[1].get('occupied_positions') != pair['occupied_positions']):
            raise ValueError('Missing pair must retain the corner source and hide only its declared source neighbor')
    return preflight


def _sample(image, xy):
    xy = np.asarray(xy, float)
    lower = np.floor(xy).astype(int)
    if (lower < 0).any() or (lower[..., 0]+1 >= image.shape[1]).any() or (lower[..., 1]+1 >= image.shape[0]).any():
        raise ValueError('Physical samples leave full native PNG')
    fraction = xy-lower
    x, y = lower[..., 0], lower[..., 1]
    fx, fy = fraction[..., 0, None], fraction[..., 1, None]
    return ((1-fx)*(1-fy)*image[y, x] + fx*(1-fy)*image[y, x+1]
            + (1-fx)*fy*image[y+1, x] + fx*fy*image[y+1, x+1])


def marker_frame(reference):
    with Image.open(read_reference(reference)) as image:
        rgba = np.asarray(image.convert('RGBA'))
    width = rgba.shape[1]
    if rgba.shape[0] % width or not np.all(rgba[..., 3] == 255):
        raise ValueError('Marker must be an opaque square or square-frame strip')
    if not np.array_equal(rgba, np.tile(rgba[:width], (len(rgba)//width, 1, 1))):
        raise ValueError('Marker frames must be byte-identical')
    return rgba[:width, :, :3].astype(float)


def _luminance(samples):
    return np.asarray(samples, float) @ np.asarray([.2126, .7152, .0722])


def _labels(values, eligible=None):
    values = _luminance(values)
    selected = values if eligible is None else values[eligible]
    if not selected.size:
        return np.zeros(values.shape, bool), 0.
    low, high = np.quantile(selected, [.1, .9])
    return values > (low+high)/2, float(high-low)


def marker_expected(marker, u, height, top, mapping='bottom'):
    """Integer bitmap lookup, independent of shader interpolation/colour transfer."""
    v = 1-height if mapping == 'bottom' else 1-height/top if mapping == 'stretch' else height
    x = np.clip(np.floor(u*marker.shape[1]/2), 0, marker.shape[1]-1).astype(int)
    y = np.clip(np.floor(v*marker.shape[0]/2), 0, marker.shape[0]-1).astype(int)
    return _labels(marker[y, x])[0]


def mask_iou(first, second, eligible=None):
    eligible = np.ones(np.shape(first), bool) if eligible is None else eligible
    union = int(np.count_nonzero((first | second) & eligible))
    return float(np.count_nonzero(first & second & eligible)/union) if union else None


def _edges(mask):
    result = np.zeros(mask.shape, bool)
    result[1:] |= mask[1:] != mask[:-1]
    result[:, 1:] |= mask[:, 1:] != mask[:, :-1]
    return result


def landmark_boundary_pixels(first, second, xy):
    """Euclidean boundary distance capped at four; four means over the budget."""
    points = [xy[_edges(mask)] for mask in (first, second)]
    if not all(len(rows) for rows in points):
        return None
    maximum = 0.
    for source, target in (points, points[::-1]):
        buckets = {}
        for point in target:
            key = tuple(np.floor(point/4).astype(int))
            buckets.setdefault(key, []).append(point)
        for point in source:
            x, y = np.floor(point/4).astype(int)
            candidates = [candidate for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                          for candidate in buckets.get((x+dx, y+dy), [])]
            if not candidates:
                return 4.
            distance = float(np.linalg.norm(np.asarray(candidates)-point, axis=1).min())
            if distance > LIMITS['maximum_boundary_pixels']:
                return 4.
            maximum = max(maximum, distance)
    return maximum


def projected_mask(geometry, projection, full_height=False, excluded=()):
    screen = tuple(int(value) for value in projection['native_image_screen'])
    image = Image.new('1', screen)
    draw = ImageDraw.Draw(image)
    for surface in geometry['surfaces']:
        position = surface['position']
        if tuple(position) in {tuple(pos) for pos in excluded}:
            continue
        x, y, z = position
        heights = [1.] * 4 if full_height else [value/255. for value in surface['heights']]
        corners = [(x, y+heights[0], z), (x+1, y+heights[1], z),
                   (x+1, y+heights[2], z+1), (x, y+heights[3], z+1)]
        toward = (np.asarray(projection['position']) - np.asarray(position) - .5
                  - np.asarray(projection.get('origin', [0, 0, 0])) if projection['kind'] == 'perspective'
                  else np.asarray(projection['toward']))
        polygons = [corners] if toward[1] > 0 and (full_height or surface['faces'] & 1) else []
        for face, (left, right) in SIDE_CORNERS.items():
            if np.dot(toward, NORMALS[face]) <= 0 or not (full_height or surface['faces'] & FACE_BITS[face]):
                continue
            a, b = corners[left], corners[right]
            polygons.append([a, b, (b[0], y, b[2]), (a[0], y, a[2])])
        for polygon in polygons:
            draw.polygon([tuple(point) for point in project(polygon, projection)], fill=1)
    return np.array(image, bool)


def excluded_pixels(declaration, geometry):
    occupied = declaration.get('occupied_positions', [])
    blocker_geometry = {'surfaces': [row for row in geometry['surfaces'] if row['position'] in occupied]}
    mask = projected_mask(blocker_geometry, declaration['projection'], full_height=True)
    mask = np.array(Image.fromarray(mask).filter(ImageFilter.MaxFilter(7)))
    for x0, y0, x1, y1 in declaration.get('excluded_rectangles', []):
        if not (0 <= x0 < x1 <= mask.shape[1] and 0 <= y0 < y1 <= mask.shape[0]):
            raise ValueError('Predeclared image exclusion is outside the complete native PNG')
        mask[y0:y1, x0:x1] = True
    return mask


def sampled_eligibility(declaration, geometry, xy):
    pixels = np.rint(xy).astype(int)
    mask = excluded_pixels(declaration, geometry)
    if (pixels < 0).any() or (pixels[..., 0] >= mask.shape[1]).any() or (pixels[..., 1] >= mask.shape[0]).any():
        raise ValueError('Physical side leaves native image')
    return ~mask[pixels[..., 1], pixels[..., 0]]


def silhouette(image, background, declaration, geometry):
    if image.shape != background.shape:
        raise ValueError('Silhouette controls have different native dimensions')
    projection = declaration['projection']
    expected = projected_mask(geometry, projection, excluded=declaration.get('occupied_positions', []))
    envelope = projected_mask(geometry, projection, full_height=True)
    selected = np.array(Image.fromarray(envelope).filter(ImageFilter.MaxFilter(7)))
    excluded = excluded_pixels(declaration, geometry)
    selected &= ~excluded
    expected &= ~excluded
    actual = difference_mask(image, background, selected)
    iou = mask_iou(actual, expected)
    edges = [_edges(mask) for mask in (actual, expected)]
    dilated = [np.asarray(Image.fromarray(mask).filter(ImageFilter.MaxFilter(7))) for mask in edges]
    boundary = bool(edges[0].any() and edges[1].any()
                    and not (edges[0] & ~dilated[1]).any() and not (edges[1] & ~dilated[0]).any())
    return {'status': 'NOT_TESTED' if iou is None else 'OBSERVED' if iou >= .95 and boundary else 'FAIL',
            'mask_iou': iou, 'all_boundary_pixels_within_3': boundary,
            'actual_pixels': int(actual.sum()), 'expected_pixels': int(expected.sum()),
            'scope': 'Full-height geometry envelope catches shader full-cube/slope/falling silhouette defects'}


def side_grid(declaration, side, geometry, common_height=None):
    surface = surface_at(geometry, side['position'], side['layer'])
    initial_u = np.asarray([.06, .94])
    top = edge_heights(surface, side['face'], initial_u)
    height = min(float(top.min()) * .9, common_height) if common_height is not None else float(top.min()) * .9
    if height <= .01:
        raise ValueError('Physical side has no measurable interior')
    projection = declaration['projection']
    bottom = project(face_points(side['position'], side['face'], initial_u, .005), projection)
    upper = project(face_points(side['position'], side['face'], initial_u, height), projection)
    columns = max(65, int(np.ceil(max(np.linalg.norm(row[1]-row[0]) for row in (bottom, upper))))+1)
    rows = max(49, int(np.ceil(np.linalg.norm(upper-bottom, axis=1).max()))+1)
    u, h = np.meshgrid(np.linspace(.06, .94, columns), np.linspace(.005, height, rows))
    xy = project(face_points(side['position'], side['face'], u, h), declaration['projection'])
    return u, h, edge_heights(surface, side['face'], u), xy


def marker_side(image, declaration, side, geometry, marker):
    preflight = side_preflight(declaration, side, geometry)
    if not preflight['adequate']:
        return {'status': 'NOT_TESTED', 'reason': 'insufficient physical viewport', 'preflight': preflight}
    u, height, top, xy = side_grid(declaration, side, geometry)
    selected = sampled_eligibility(declaration, geometry, xy)
    observed, contrast = _labels(_sample(image, xy), selected)
    expected = marker_expected(marker, u, height, top)
    # Remove planned bitmap edges, where interpolation is deliberately ambiguous.
    boundary = np.zeros(expected.shape, bool)
    boundary[1:] |= expected[1:] != expected[:-1]
    boundary[:, 1:] |= expected[:, 1:] != expected[:, :-1]
    boundary = np.asarray(Image.fromarray(boundary).filter(ImageFilter.MaxFilter(3)))
    eligible = ~boundary & selected
    count = int(eligible.sum())
    iou = mask_iou(observed, expected, eligible)
    boundary_pixels = landmark_boundary_pixels(observed & selected, expected & selected, xy)
    flips = {'flip_u': mask_iou(observed, marker_expected(marker, 1-u, height, top), eligible),
             'flip_v': mask_iou(observed, marker_expected(marker, u, height, top, 'top'), eligible),
             'stretch': mask_iou(observed, marker_expected(marker, u, height, top, 'stretch'), eligible)}
    discrimination = {name: mask_iou(expected, marker_expected(marker, (1-u if name == 'flip_u' else u),
                                         height, top, ('top' if name == 'flip_v' else
                                                       'stretch' if name == 'stretch' else 'bottom')), eligible)
                      for name in flips}
    adequate = contrast >= LIMITS['minimum_marker_contrast'] and count >= LIMITS['minimum_marker_samples']
    unique = all(value is not None and value < LIMITS['minimum_mask_iou'] for value in discrimination.values())
    status = ('NOT_TESTED' if not adequate or not unique else 'OBSERVED'
              if iou >= .95 and boundary_pixels is not None and boundary_pixels <= 3 else 'FAIL')
    return {'status': status, 'eligible_samples': count, 'contrast': contrast, 'marker_mask_iou': iou,
            'wrong_mapping_iou': flips, 'marker_discrimination_iou': discrimination,
            'landmark_boundary_euclidean_capped_pixels': boundary_pixels,
            'preflight': preflight, 'scope': 'Spatial binary landmark ordering, not source RGB transfer'}


def crop_registration(high_image, low_image, high, low, high_side, low_side, marker):
    hg, lg = builtin_geometry(high['source_id']), builtin_geometry(low['source_id'])
    preflight = side_preflight(low, low_side, lg)
    if not preflight['adequate']:
        return {'status': 'NOT_TESTED', 'reason': 'low side projects below 24 pixels', 'preflight': preflight}
    if high_side['face'] != low_side['face']:
        raise ValueError('Crop registration requires the same canonical face')
    ls = surface_at(lg, low_side['position'], low_side['layer'])
    common = min(ls['heights'])/255*.9
    u, height, high_top, high_xy = side_grid(high, high_side, hg, common)
    lu, lh, low_top, low_xy = side_grid(low, low_side, lg, common)
    if not np.array_equal(u, lu) or not np.array_equal(height, lh):
        raise ValueError('Crop grid differs at equal physical heights')
    eligible = sampled_eligibility(high, hg, high_xy) & sampled_eligibility(low, lg, low_xy)
    a, ca = _labels(_sample(high_image, high_xy), eligible)
    b, cb = _labels(_sample(low_image, low_xy), eligible)
    expected = marker_expected(marker, u, height, high_top)
    iou = mask_iou(a, b, eligible)
    boundaries = [landmark_boundary_pixels(a & eligible, b & eligible, points) for points in (high_xy, low_xy)]
    boundary = max(boundaries) if all(value is not None for value in boundaries) else math.inf
    fidelity = [mask_iou(a, expected, eligible), mask_iou(b, expected, eligible)]
    wrong = mask_iou(marker_expected(marker, u, height, high_top, 'stretch'),
                     marker_expected(marker, u, height, low_top, 'stretch'), eligible)
    adequate = min(ca, cb) >= 12 and eligible.sum() >= 80 and wrong is not None and wrong < .95
    status = ('NOT_TESTED' if not adequate else 'OBSERVED'
              if iou >= .95 and min(fidelity) >= .95 and boundary <= 3 else 'FAIL')
    return {'status': status, 'equal_height_mask_iou': iou, 'canonical_marker_iou': fidelity,
            'stretched_wrong_control_iou': wrong, 'common_height': common,
            'landmark_boundary_euclidean_capped_pixels': boundary if math.isfinite(boundary) else None,
            'scope': 'Equal physical (u,height) registration; no RGB fit or sampler inference'}


def normalized_surfaces(rows):
    """Flatten split transport parts by logical position/layer, ignoring regrouping."""
    result = {}
    for row in rows:
        key = tuple(row['position']), row['layer']
        heights = tuple(row['heights'])
        if len(heights) != 4 or any(type(h) is not int or not 0 <= h <= 255 for h in heights):
            raise ValueError('Observed surfaces need four integer height bytes')
        faces = row['faces']
        if type(faces) is not int or not 0 < faces <= 63:
            raise ValueError('Observed surface part has invalid faces')
        entry = result.setdefault(key, {'heights': heights, 'faces': 0, 'parts': []})
        if entry['heights'] != heights or entry['faces'] & faces:
            raise ValueError('Split surface repeats faces or disagrees on corners')
        entry['faces'] |= faces
        entry['parts'].append((faces, row['texture'], row['template'], row['rotation'], tuple(row['tint'])))
    return {key: {'heights': value['heights'], 'faces': value['faces'],
                  'parts': sorted(value['parts'], key=lambda row: row[0])} for key, value in result.items()}


def decode_groups(groups):
    """Decode captured owner uniforms directly, without using runtime transport math."""
    rows = []
    for group in groups:
        origin, uniforms = group['origin'], np.asarray(group['uniforms'], float)
        if (len(origin) != 3 or any(type(value) is not int for value in origin)
                or uniforms.shape != (4, 4) or not np.isfinite(uniforms).all()):
            raise ValueError('Captured group has invalid origin/uniforms')
        tag = uniforms[3, 0]
        if tag != 39686 and (tag != int(tag) or not 0 <= tag <= 16777215 or int(tag) % 256 != 134):
            raise ValueError('Captured group has no world/UI liquid payload tag')
        pairs = uniforms[1:3].reshape(-1)
        if any(value != int(value) or not 0 <= value <= 65535 for value in pairs):
            raise ValueError('Captured height pairs are not exact unsigned words')
        tint = uniforms[3, 2]
        if tint != int(tint) or not 0 <= tint <= 16777215:
            raise ValueError('Captured tint is not an exact RGB word')
        if group.get('visible') is False:
            continue
        for slot, value in enumerate(uniforms[0]):
            if value != int(value) or not 0 <= value < 1048576:
                raise ValueError('Captured address/face/rotation word is invalid')
            code = int(value)
            faces = (code // 64) % 64
            if not faces:
                continue
            address = code % 64
            position = [origin[0]+address % 4, origin[1]+address // 16, origin[2]+address // 4 % 4]
            first, last = (int(pairs[2*slot+i]) for i in (0, 1))
            rows.append({'position': position, 'layer': group['layer'], 'faces': faces,
                         'heights': [first % 256, first // 256, last % 256, last // 256],
                         'texture': group['texture'], 'template': group['template'], 'rotation': code // 4096,
                         'tint': [int(tint)//65536, int(tint)//256 % 256, int(tint) % 256]})
    return rows


def state_surfaces(state):
    rows = decode_groups(state['groups']) if 'groups' in state else state['quantized_surfaces']
    if 'groups' in state and 'quantized_surfaces' in state:
        if normalized_surfaces(rows) != normalized_surfaces(state['quantized_surfaces']):
            raise ValueError('Reported surfaces disagree with captured owner payload')
    return rows


def geometry_state(state, geometry, excluded=()):
    if state.get('ready') is not True:
        return {'status': 'NOT_TESTED', 'reason': 'ordinary owner is not ready'}
    actual = normalized_surfaces(state_surfaces(state))
    expected = {(tuple(row['position']), row['layer']): row for row in geometry['surfaces']
                if tuple(row['position']) not in {tuple(pos) for pos in excluded}}
    exact = (state['source_cells'] == geometry['source_cells'] and set(actual) == set(expected)
             and all(actual[key]['heights'] == tuple(row['heights']) and actual[key]['faces'] == row['faces']
                     for key, row in expected.items()))
    return {'status': 'OBSERVED' if exact else 'FAIL', 'exact_source_geometry': exact,
            'observed_surfaces': len(actual), 'expected_surfaces': len(expected)}


def missing_invariant(before, occupied, restored, positions):
    base, hidden, final = (normalized_surfaces(state_surfaces(row)) for row in (before, occupied, restored))
    removed = {key for key in base if key[0] in {tuple(pos) for pos in positions}}
    expected = {key: value for key, value in base.items() if key not in removed}
    source = before['source_cells'] == occupied['source_cells'] == restored['source_cells']
    settled = all(row.get('ready') is True and row.get('occupancy_settled') is True
                  for row in (before, occupied, restored))
    exact = bool(removed) and hidden == expected and final == base and source
    return {'status': 'NOT_TESTED' if not settled else 'OBSERVED' if exact else 'FAIL',
            'retained_source': source, 'removed_logical_surfaces': len(removed),
            'survivors_exact': hidden == expected, 'restored_exact': final == base,
            'scope': 'Includes corners, hidden faces and material parts; ignores group/model IDs'}


def _status(rows):
    statuses = [row['status'] for row in rows]
    return 'FAIL' if 'FAIL' in statuses else 'NOT_TESTED' if not statuses or 'NOT_TESTED' in statuses else 'OBSERVED'


def projection_stable(state, declaration):
    return (state.get('projection_before') == declaration['projection']
            and state.get('projection_after') == declaration['projection'])


def analyze(plan_path, evidence_path):
    plan = json.loads(Path(plan_path).read_bytes())
    preflight = validate_plan(plan)
    evidence = json.loads(Path(evidence_path).read_bytes())
    if read_reference(evidence['plan']).resolve() != Path(plan_path).resolve():
        raise ValueError('Evidence names another plan')
    receipt = json.loads(read_reference(evidence['preflight']).read_bytes())
    if receipt.get('plan_sha256') != fingerprint(plan_path)['sha256'] or receipt.get('geometry') != preflight:
        raise ValueError('Pre-capture receipt does not bind exact source-driven geometry')
    if type(receipt.get('created_qpc_100ns')) is not int or receipt['created_qpc_100ns'] <= 0:
        raise ValueError('Pre-capture receipt needs a positive capture-clock QPC timestamp')
    failures = capture_failures(evidence.get('captures', {}), evidence['session_binding'])
    declarations = {row['id']: row for row in plan['declarations']}
    if set(evidence.get('captures', {})) != set(declarations):
        failures.append('Exact finite capture set is incomplete or contains undeclared images')
    if not all(evidence.get(key) is True for key in ('completed', 'restored')) or evidence.get('cleanup_errors'):
        failures.append('Capture batch did not complete and restore')
    for identity, capture in evidence.get('captures', {}).items():
        if identity in declarations and [capture.get('width'), capture.get('height')] != declarations[identity]['projection']['native_image_screen']:
            failures.append('Capture dimensions differ from full declared native viewport: ' + identity)
        if capture['frame']['frame_qpc_100ns'] <= receipt.get('created_qpc_100ns', math.inf):
            failures.append('Capture predates geometry preflight: ' + identity)
    output = {'schema': 1, 'plan': fingerprint(plan_path), 'evidence': fingerprint(evidence_path),
              'analyzer': fingerprint(__file__), 'limits': LIMITS, 'capture_failures': failures,
              'preflight': preflight, 'geometry': {}, 'sides': {}, 'crop_pairs': {}, 'missing': {},
              'silhouettes': {}, 'coverage': {},
              'original_art': {'status': 'NOT_TESTED'}, 'visible_side_correctness_observed': False,
              'structural_status': 'NOT_TESTED',
              'native_uv_accepted': False, 'native_source_color_transfer_accepted': False,
              'native_animation_accepted': False, 'production_accepted': False}
    if failures:
        return output
    images = {identity: rgb(capture['path']) for identity, capture in evidence['captures'].items()}
    marker = marker_frame(plan['marker']) if plan.get('marker') else None
    states = evidence['states']
    for identity, declaration in declarations.items():
        geometry = builtin_geometry(declaration['source_id'], declaration['control'])
        state = states[identity]
        if not projection_stable(state, declaration):
            output['geometry'][identity] = {'status': 'FAIL', 'reason': 'camera/viewport/source projection drift'}
            continue
        if declaration['route'] == 'native':
            output['geometry'][identity] = {'status': 'NOT_TESTED',
                                           'reason': 'Native pixels require bound exact source readbacks'}
        else:
            if evidence.get('evidence_kind') == 'physical_native_capture' and not isinstance(state.get('groups'), list):
                raise ValueError('Physical candidate state needs captured applied owner groups: ' + identity)
            output['geometry'][identity] = geometry_state(state, geometry, declaration.get('occupied_positions', []))
        if declaration['role'] == 'marker' and marker is not None:
            output['sides'][identity] = [marker_side(images[identity], declaration, side, geometry, marker)
                                         for side in declaration['sides']]
            background = declaration.get('background_id')
            if declaration['control'] == 'supported_positive':
                output['silhouettes'][identity] = (silhouette(images[identity], images[background], declaration, geometry)
                    if background else {'status': 'NOT_TESTED', 'reason': 'No topology-aligned support-only baseline'})
    for pair in plan.get('crop_pairs', []):
        high, low = pair['high'], pair['low']
        if marker is None:
            output['crop_pairs'][pair['id']] = {'status': 'NOT_TESTED', 'reason': 'no frozen marker'}
            continue
        output['crop_pairs'][pair['id']] = crop_registration(images[high], images[low], declarations[high],
            declarations[low], pair['high_side'], pair['low_side'], marker)
    for pair in plan.get('missing_pairs', []):
        output['missing'][pair['id']] = missing_invariant(states[pair['baseline']], states[pair['occupied']],
                                                          states[pair['restored']], pair['occupied_positions'])
    output['original_art'] = original_review(plan, evidence, declarations)
    output['coverage'] = coverage(plan)
    rows = [row for key, row in output['geometry'].items()
            if declarations[key]['route'] != 'native' or row['status'] == 'FAIL']
    rows += list(output['crop_pairs'].values()) + list(output['missing'].values()) + list(output['silhouettes'].values())
    rows += [row for sides in output['sides'].values() for row in sides]
    output['structural_status'] = _status(rows)
    output['visible_side_correctness_observed'] = (all(output['coverage'].values())
                                                   and _status(rows + [output['original_art']]) == 'OBSERVED'
                                                   and evidence.get('evidence_kind') == 'physical_native_capture')
    return output


def original_review(plan, evidence, declarations):
    pairs = plan.get('original_pairs', [])
    if not pairs or not evidence.get('original_review'):
        return {'status': 'NOT_TESTED', 'reason': 'actual native original-art reference and independent review required'}
    review = json.loads(read_reference(evidence['original_review']).read_bytes())
    if review.get('plan_sha256') != evidence['plan']['sha256'] or not review.get('reviewer'):
        raise ValueError('Original-art review has no exact plan/reviewer binding')
    artwork = plan.get('original_artwork', {})
    expected_artwork = {'still': 'db3edc3132d88a595d466e90840a8e8839593776421435c23aa880fbd2a779c3',
                        'flow': 'f803fa03de42513b8e19db50e8c0743c5c82a06337afe0191efddd3e47684246'}
    if set(artwork) != set(expected_artwork):
        return {'status': 'NOT_TESTED', 'reason': 'Original installed still/flow PNG references are absent'}
    for key, reference in artwork.items():
        if reference['sha256'] != expected_artwork[key]:
            raise ValueError('Original artwork SHA differs from frozen installed native source')
        read_reference(reference)
    results = []
    for pair in pairs:
        candidate, native = declarations[pair['candidate']], declarations[pair['native']]
        if candidate['role'] != 'original' or native['role'] != 'native_original':
            raise ValueError('Original-art pair needs candidate and actual native original roles')
        if candidate['source_id'] != native['source_id'] or candidate['view'] != native['view']:
            raise ValueError('Original-art pair changes source or view')
        row = review.get('pairs', {}).get(pair['id'], {})
        hashes = {key: evidence['captures'][pair[key]]['sha256'] for key in ('candidate', 'native')}
        exact = row.get('capture_sha256') == hashes
        native_state = evidence['states'][pair['native']]
        projections_stable = all(projection_stable(evidence['states'][pair[key]], declarations[pair[key]])
                                 for key in ('candidate', 'native'))
        readbacks = native_state.get('native_readbacks')
        stable = False
        if readbacks:
            observation = json.loads(read_reference(readbacks).read_bytes())
            expected = builtin_geometry(native['source_id'], native['control'])['native_readback_cells']
            stable = (observation.get('session_binding') == evidence['session_binding']
                      and observation.get('before') == expected and observation.get('after') == expected
                      and observation.get('flow_frozen') is True and observation.get('original_artwork') == artwork)
        properties = ('four_face_direction', 'physical_height_crop', 'original_side_artwork', 'original_top_artwork')
        values = [row.get(key, 'NOT_TESTED') for key in properties]
        if any(value not in ('OBSERVED', 'FAIL', 'NOT_TESTED') for value in values):
            raise ValueError('Original direct review properties need explicit observation statuses')
        status = ('FAIL' if not projections_stable else 'NOT_TESTED' if not exact or not stable
                  else _status([{'status': value} for value in values]))
        results.append({'id': pair['id'], 'status': status, 'capture_hashes_bound': exact,
                        'native_source_bound': stable, 'projections_stable': projections_stable})
    return {'status': _status(results), 'pairs': results,
            'scope': 'Recorded direct review of native original pixels; no native absolute RGB/filter/timing promotion'}


def coverage(plan):
    positive = [row for row in plan['declarations'] if row['control'] == 'supported_positive']
    marker = [row for row in positive if row['role'] == 'marker' and row['route'] != 'native']
    sides = {(row['route'], row['source_id'], side['face']) for row in marker for side in row['sides']}
    required = {(route, source, face) for route in ROUTES[:3] for source in SOURCE_IDS[:2] for face in SIDE_CORNERS}
    by_id = {row['id']: row for row in plan['declarations']}
    crop = {(by_id[row['high']]['route'], row['high_side']['face']) for row in plan.get('crop_pairs', [])
            if by_id[row['high']]['source_id'] == SOURCE_IDS[0] and by_id[row['low']]['source_id'] == SOURCE_IDS[1]
            and by_id[row['high']]['route'] == by_id[row['low']]['route']}
    contexts = {(row['route'], row['source_id']) for row in marker}
    original = {(by_id[row['candidate']]['route'], by_id[row['candidate']]['source_id'], by_id[row['candidate']]['view'])
                for row in plan.get('original_pairs', [])}
    original_required = {(route, source, view) for route in ROUTES[:3] for source in SOURCE_IDS
                         for view in (('vnw', 'vse') if source in SOURCE_IDS[:2] else ('vnw',))}
    return {'four_face_marker': required.issubset(sides),
            'equal_height_crop': {(route, face) for route in ROUTES[:3] for face in SIDE_CORNERS}.issubset(crop),
            'sloped_falling': {(route, source) for route in ROUTES[:3] for source in SOURCE_IDS[2:]}.issubset(contexts),
            'occupied_neighbor': bool(plan.get('missing_pairs')),
            'native_original_holdout': original_required.issubset(original)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--geometry', choices=SOURCE_IDS)
    args = parser.parse_args()
    if args.output.exists() or args.output.with_suffix('.sources').exists():
        parser.error('Choose a fresh immutable output and source archive')
    if args.geometry:
        result = builtin_geometry(args.geometry)
        result['source_bindings'] = source_bindings()
    elif args.plan and not args.input:
        geometry = validate_plan(json.loads(args.plan.read_bytes()))
        ready = all(row['adequate'] for rows in geometry.values() for row in rows)
        result = {'schema': 1, 'plan_sha256': fingerprint(args.plan)['sha256'],
                  'geometry': geometry, 'preflight_geometry_ready': ready,
                  'status': 'NOT_TESTED', 'visible_side_correctness_observed': False}
    elif args.plan and args.input:
        result = analyze(args.plan, args.input)
    else:
        parser.error('Use --geometry, --plan for offline preflight, or --plan with --input for replay')
    for flag in ('native_uv_accepted', 'native_source_color_transfer_accepted',
                 'native_animation_accepted', 'production_accepted'):
        result[flag] = False
    result.setdefault('status', 'NOT_TESTED')
    result.setdefault('visible_side_correctness_observed', False)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    archive = args.output.with_suffix('.sources')
    archive.mkdir()
    for name in BOUND_FILES:
        target = archive/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT/name, target)
    result['analyzer_sources'] = {name: fingerprint(archive/name) for name in BOUND_FILES}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'output': str(args.output.resolve()),
                      'visible_side_correctness_observed': result.get('visible_side_correctness_observed', False)}))
    success = (bool(args.geometry) or result.get('preflight_geometry_ready') is True
               or result.get('visible_side_correctness_observed') is True)
    return 0 if success else 1


if __name__ == '__main__':
    raise SystemExit(main())
