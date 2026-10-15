"""Independent north-frame cube pose diagnostics across front and oblique views."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_fill_holes
from scipy.optimize import least_squares
from scipy.spatial import cKDTree

from analyze_frame_block_pose_r21 import boundary, polygon, project, support, vertices
from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from analyze_visible_items_r16 import target
from camera_projection import project_points
from item_sprite_capture_contract import camera_matches, snapshot_digest

CANDIDATE = [.25, 0., 0., .4375]
ANGLES = (-75., 0., 75.)
DIRECTIONS = np.column_stack((np.cos(np.arange(360) * np.pi / 180.),
                              np.sin(np.arange(360) * np.pi / 180.)))
LIMITS = {'support_rms_pixels': 2., 'support_max_pixels': 4.,
          'paired_iou': .9, 'paired_edge_p95_pixels': 2.5,
          'minimum_stable_fraction': .95}


def visible_vertices(position, parameters):
    """Clip the cube at the independently known solid support's north plane."""
    result = vertices(position, parameters)
    return [(x, y, min(z, position[2] + 1.)) for x, y, z in result]


def clipping_certified(position, parameters, camera):
    plane = position[2] + 1.
    eye = camera['position']
    if eye[2] >= plane:
        return False
    for point in vertices(position, parameters):
        if point[2] <= plane:
            continue
        ratio = (plane - eye[2]) / (point[2] - eye[2])
        hit = [eye[axis] + ratio * (point[axis] - eye[axis]) for axis in (0, 1)]
        if not all(position[axis] <= hit[axis] <= position[axis] + 1. for axis in (0, 1)):
            return False
    return min(point[2] for point in vertices(position, parameters)) < plane


def project_visible(view, parameters):
    points = project_points(visible_vertices(view['position'], parameters),
        view['camera']['position'], target(view['camera']), view['size'], view['fov'])
    if min(point['depth'] for point in points) <= .05:
        raise ValueError('Visible cube crosses the camera near plane')
    return np.array([(point['screenX'], point['screenY']) for point in points])


def residual(view, parameters):
    return support(project_visible(view, parameters), DIRECTIONS) - view['observed_support']


def geometry_row(view, parameters):
    if len(view['contour']) < 3 or not np.isfinite(view['contour']).all():
        return {'support_rms_pixels': None, 'support_max_pixels': None,
                'support_clipping_certified': False, 'passed': False}
    errors = residual(view, parameters)
    rms, maximum = float(np.sqrt(np.mean(errors ** 2))), float(np.max(abs(errors)))
    certified = clipping_certified(view['position'], parameters, view['camera'])
    return {'support_rms_pixels': rms, 'support_max_pixels': maximum,
            'support_clipping_certified': certified,
            'passed': certified and rms <= LIMITS['support_rms_pixels'] and
                      maximum <= LIMITS['support_max_pixels']}


def joint_fit(views):
    if not views:
        raise ValueError('No native cube views')
    fit = least_squares(lambda values: np.concatenate([residual(view, values) for view in views]),
        CANDIDATE, bounds=([.05, -.2, -.2, -.2], [.8, .2, .2, .8]),
        max_nfev=400, xtol=1e-12, ftol=1e-12, gtol=1e-10)
    singular = np.linalg.svd(fit.jac, compute_uv=False)
    angles = set(view['angle'] for view in views)
    full_rank = singular[-1] > singular[0] * 1e-6
    holdouts = len(angles) >= 3 and set(ANGLES).issubset(angles)
    return {'parameters_scale_cx_cy_cz': fit.x.tolist(),
            'support_rms_pixels': float(np.sqrt(np.mean(fit.fun ** 2))),
            'support_max_pixels': float(np.max(abs(fit.fun))),
            'jacobian_singular_values': singular.tolist(), 'view_angles': sorted(angles),
            'jacobian_full_rank': bool(full_rank), 'holdout_views_present': bool(holdouts),
            'depth_identifiable': bool(full_rank and holdouts),
            'support_clipping_certified': all(clipping_certified(view['position'], fit.x, view['camera']) for view in views)}


def paired(native, product):
    assert camera_matches(native['camera'], product['camera'])
    assert native['size'] == product['size']
    first, second = native['mask'], product['mask']
    union = int((first | second).sum())
    iou = float((first & second).sum() / union) if union else 0.
    edges = np.concatenate((cKDTree(native['contour']).query(product['contour'])[0],
                            cKDTree(product['contour']).query(native['contour'])[0]))
    p95 = float(np.percentile(edges, 95))
    return {'iou': iou, 'edge_p95_pixels': p95, 'edge_max_pixels': float(edges.max()),
            'passed': bool(union and iou >= LIMITS['paired_iou'] and p95 <= LIMITS['paired_edge_p95_pixels'])}


def observe(case, route, captures, fov):
    prefix = case['id'] + '_' + route
    row = captures[prefix + '_shown']
    before, after = (captures[prefix + '_' + suffix] for suffix in ('hidden_before', 'hidden_after'))
    assert camera_matches(row['camera'], before['camera']) and camera_matches(row['camera'], after['camera'])
    shown, first, last = (rgb(value['capture']['path']) for value in (row, before, after))
    assert shown.shape == first.shape == last.shape
    position = case['native_reference']['prepare']['rows'][0]['position']
    view = {'position': position, 'camera': row['camera'], 'size': (shown.shape[1], shown.shape[0]),
            'fov': fov, 'angle': case['source'].get('view_angle_degrees', 0.)}
    frame = project(position, [1., 0., 0., 0.], row['camera'], view['size'], fov)
    lo = np.maximum(0, np.floor(frame.min(axis=0) - 8).astype(int))
    hi = np.minimum(view['size'], np.ceil(frame.max(axis=0) + 8).astype(int))
    selected = np.zeros(shown.shape[:2], dtype=bool)
    selected[lo[1]:hi[1], lo[0]:hi[0]] = True
    assert selected.any(), 'Declared frame envelope is offscreen'
    stable = np.max(abs(first - last), axis=2) <= 3
    stable_fraction = float(stable[selected].mean())
    assert stable_fraction >= LIMITS['minimum_stable_fraction'], 'Hidden controls drifted'
    mask = binary_fill_holes(difference_mask(shown, (first.astype(float) + last) / 2., selected, 8) & stable)
    contour = boundary(mask)
    assert len(contour) > 16, 'No independently differenced cube body'
    view.update(mask=mask, contour=contour, observed_support=support(contour, DIRECTIONS),
                shown=shown, lo=lo, hi=hi, stable_fraction=stable_fraction)
    return view


def analyze(source, output):
    report = json.loads(source.read_bytes())
    assert report['completed'] and report['matrix_completed'] and not report['cleanup_errors']
    assert report['source_unchanged'] and report['launch_sources'] == report['sources_after']
    assert snapshot_digest(report['launch_sources']) == report['launch_sources_sha256']
    assert not report['native_item_shader_errors']
    captures = {row['label']: row for row in report['captures']}
    assert not capture_failures({key: row['capture'] for key, row in captures.items()}, report['session'])
    calibration = report['camera_calibration']
    assert calibration['passed'] and calibration['restored'] and not calibration['cleanup_errors']
    output.mkdir(parents=True, exist_ok=False)
    result = {'schema': 1, 'production_qualified': False, 'geometry_holdouts_passed': False,
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'source': str(source.resolve()), 'limits': LIMITS, 'candidate': CANDIDATE,
              'scope': 'Fixed north-facing rotation-zero cube geometry with solid north support plane; material and glint unaccepted',
              'limitations': ['One camera without a verified support occlusion model cannot resolve absolute scale and depth; this clipped model adds the independently known support plane as a constraint',
                  'Support clipping is accepted as a geometric model only when every removed vertex ray intersects the actual full-cube support',
                  'Joint fit diagnoses remaining error and does not replace the predeclared candidate for holdout scoring',
                  'Six faces, eight rotations, UI pixels, lighting, textures and glint require separate native acceptance'],
              'cases': []}
    native_views = []
    by_item = {}
    for case in report['cases']:
        assert case['measurement_completed'] and case['native_reference']['restored']
        assert case['source']['facing'] == 2 and case['source']['rotation_degrees'] == 0
        views = {route: observe(case, route, captures, calibration['vertical_fov']) for route in ('native', 'full', 'missing')}
        native_views.append(views['native'])
        by_item.setdefault(tuple(case['source']['item']), []).append(views['native'])
        measured = {'id': case['id'], 'item': case['source']['item'], 'angle': views['native']['angle'],
                    'routes': {}, 'native_product': {}}
        for route, view in views.items():
            fixed = geometry_row(view, CANDIDATE)
            shifted = dict(view, observed_support=support(view['contour'] + [8., 0.], DIRECTIONS))
            blank = dict(view, contour=np.empty((0, 2)), observed_support=None)
            fixed['negative_controls'] = {'blank_rejected': not geometry_row(blank, CANDIDATE)['passed'],
                                           'shifted_rejected': not geometry_row(shifted, CANDIDATE)['passed']}
            measured['routes'][route] = {'observed': mask_row(view['mask']), 'stable_fraction': view['stable_fraction'],
                'candidate': fixed, 'observed_hull': polygon(view['contour']).tolist(),
                'candidate_visible_hull': polygon(project_visible(view, CANDIDATE)).tolist(),
                'candidate_complete_hull': polygon(project(view['position'], CANDIDATE, view['camera'], view['size'], view['fov'])).tolist()}
            crop = Image.fromarray(view['shown'].astype(np.uint8)).crop((*view['lo'], *view['hi'])).convert('RGB')
            draw = ImageDraw.Draw(crop)
            for points, color in ((polygon(view['contour']), (20, 240, 40)),
                                  (polygon(project_visible(view, CANDIDATE)), (20, 220, 255))):
                line = [tuple(point - view['lo']) for point in points]
                draw.line(line + line[:1], fill=color, width=1)
            crop.resize((crop.width * 2, crop.height * 2)).save(output / (case['id'] + '-' + route + '-hull.png'))
            Image.fromarray(view['mask']).save(output / (case['id'] + '-' + route + '-mask.png'))
        for route in ('full', 'missing'):
            measured['native_product'][route] = paired(views['native'], views[route])
        result['cases'].append(measured)
    result['joint_native_fit'] = joint_fit(native_views)
    result['per_item_native_fit'] = [{'item': list(item), 'fit': joint_fit(views)} for item, views in by_item.items()]
    complete = all(set(view['angle'] for view in views) == set(ANGLES) for views in by_item.values())
    result['geometry_holdouts_passed'] = bool(complete and result['joint_native_fit']['depth_identifiable'] and
        result['joint_native_fit']['support_clipping_certified'] and all(
            all(row['candidate']['passed'] and all(row['candidate']['negative_controls'].values()) for row in case['routes'].values()) and
            all(row['passed'] for row in case['native_product'].values()) for case in result['cases']))
    (output / 'multiview.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    result = analyze(args.source, args.output)
    print(json.dumps({key: result[key] for key in ('geometry_holdouts_passed', 'joint_native_fit', 'production_qualified')}))
