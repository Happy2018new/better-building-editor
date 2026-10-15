"""Offline independent cube hull diagnostics for a restored actual frame case."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, binary_fill_holes
from scipy.optimize import least_squares
from scipy.spatial import ConvexHull

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_liquid_workspace import capture_failures, difference_mask, mask_row, rgb
from analyze_visible_items_r16 import target
from camera_projection import project_points
from item_sprite_capture_contract import camera_matches, snapshot_digest


def vertices(position, parameters):
    scale, cx, cy, cz = parameters
    return [(position[0] + .5 - cx - x * scale,
             position[1] + .5 + cy + y * scale,
             position[2] + .5 + cz + z * scale)
            for x in (-.5, .5) for y in (-.5, .5) for z in (-.5, .5)]


def project(position, parameters, camera, size, fov):
    points = project_points(vertices(position, parameters), camera['position'], target(camera), size, fov)
    if min(point['depth'] for point in points) <= .05:
        raise ValueError('Cube crosses the near plane')
    return np.array([(point['screenX'], point['screenY']) for point in points])


def support(points, directions):
    return np.max(points @ directions.T, axis=0)


def boundary(mask):
    ys, xs = np.nonzero(mask & ~binary_erosion(mask))
    return np.column_stack((xs + .5, ys + .5))


def polygon(points):
    return points[ConvexHull(points).vertices]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    report = json.loads(args.source.read_bytes())
    assert report['completed'] and not report['cleanup_errors'] and report['source_unchanged']
    assert report['launch_sources'] == report['sources_after']
    assert snapshot_digest(report['launch_sources']) == report['launch_sources_sha256']
    assert not report['native_item_shader_errors']
    case = report['cases'][0]
    assert case['measurement_completed'] and case['native_reference']['restored']
    assert case['source']['facing'] == 2 and case['source']['rotation_degrees'] == 0
    captures = {row['label']: row for row in report['captures']}
    failures = capture_failures({key: row['capture'] for key, row in captures.items()}, report['session'])
    assert not failures, failures
    position = case['native_reference']['prepare']['rows'][0]['position']
    fov = report['camera_calibration']['vertical_fov']
    angles = np.arange(360) * np.pi / 180.
    directions = np.column_stack((np.cos(angles), np.sin(angles)))
    args.output.mkdir(parents=True, exist_ok=False)
    results = {'schema': 1, 'production_qualified': False, 'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
               'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'source': str(args.source.resolve()), 'position': position, 'vertical_fov': fov, 'routes': {},
               'limits': ['One native camera is insufficient for six-face, rotation or depth acceptance',
                          'Observed differences are measured independently of the generated cube mesh',
                          'Fitted pose is a candidate and does not accept material, lighting or glint']}
    old_pose = [.5, 0., 0., .1875]
    proposed = [.25, 0., 0., .4375]
    for route in ('native', 'full', 'missing'):
        prefix = case['id'] + '_' + route
        row = captures[prefix + '_shown']
        before, after = (captures[prefix + '_' + suffix] for suffix in ('hidden_before', 'hidden_after'))
        assert camera_matches(row['camera'], before['camera']) and camera_matches(row['camera'], after['camera'])
        shown = rgb(row['capture']['path'])
        first, last = rgb(before['capture']['path']), rgb(after['capture']['path'])
        hidden = (first.astype(float) + last) / 2.
        stable = np.max(abs(first - last), axis=2) <= 3
        size = (shown.shape[1], shown.shape[0])
        frame = project(position, [1., 0., 0., 0.], row['camera'], size, fov)
        lo = np.maximum(0, np.floor(frame.min(axis=0) - 8).astype(int))
        hi = np.minimum(size, np.ceil(frame.max(axis=0) + 8).astype(int))
        selected = np.zeros(shown.shape[:2], dtype=bool)
        selected[lo[1]:hi[1], lo[0]:hi[0]] = True
        observed = difference_mask(shown, hidden, selected, 8) & stable
        contour = boundary(binary_fill_holes(observed))
        assert len(contour) > 16
        observed_support = support(contour, directions)

        def residual(parameters):
            return support(project(position, parameters, row['camera'], size, fov), directions) - observed_support

        fit = least_squares(residual, proposed if route == 'native' else old_pose,
                            bounds=([.05, -.25, -.25, -.25], [.8, .25, .25, .8]),
                            xtol=1e-12, ftol=1e-12, gtol=1e-10, max_nfev=300)
        centered = least_squares(lambda values: residual([values[0], 0., 0., values[1]]),
                                 [proposed[0], proposed[3]] if route == 'native' else [old_pose[0], old_pose[3]],
                                 bounds=([.05, -.25], [.8, .8]), max_nfev=300,
                                 xtol=1e-12, ftol=1e-12, gtol=1e-10)
        sensitivity = []
        for candidate_fov in sorted(set([fov] + report['camera_calibration']['individual_fitted_vertical_fov'])):
            constrained = least_squares(lambda values: support(project(position,
                [values[0], 0., 0., values[1]], row['camera'], size, candidate_fov), directions) - observed_support,
                centered.x, bounds=([.05, -.25], [.8, .8]), max_nfev=300)
            sensitivity.append({'fov': candidate_fov, 'scale': float(constrained.x[0]),
                                'center_z': float(constrained.x[1]),
                                'rms': float(np.sqrt(np.mean(constrained.fun ** 2)))})
        projected = project(position, fit.x, row['camera'], size, fov)
        simple = project(position, proposed, row['camera'], size, fov)
        results['routes'][route] = {'observed': mask_row(observed), 'stable_fraction': float(stable[selected].mean()),
            'fit_parameters_scale_cx_cy_cz': fit.x.tolist(), 'fit_support_rms_pixels': float(np.sqrt(np.mean(fit.fun ** 2))),
            'fit_max_support_pixels': float(np.max(abs(fit.fun))),
            'fit_jacobian_singular_values': np.linalg.svd(fit.jac, compute_uv=False).tolist(),
            'frame_centered_fit_scale_cz': centered.x.tolist(),
            'frame_centered_fit_support_rms_pixels': float(np.sqrt(np.mean(centered.fun ** 2))),
            'fov_sensitivity_centered_fit': sensitivity,
            'old_pose_support_rms_pixels': float(np.sqrt(np.mean(residual(old_pose) ** 2))),
            'quarter_cube_support_rms_pixels': float(np.sqrt(np.mean(residual(proposed) ** 2))),
            'quarter_cube_max_support_pixels': float(np.max(abs(residual(proposed)))),
            'observed_hull': polygon(contour).tolist(), 'fitted_hull': polygon(projected).tolist()}
        crop = Image.fromarray(shown.astype(np.uint8)).crop((lo[0], lo[1], hi[0], hi[1])).convert('RGB')
        draw = ImageDraw.Draw(crop)
        for points, color in ((polygon(contour), (20, 240, 40)), (polygon(projected), (240, 40, 220)),
                              (polygon(simple), (20, 220, 255))):
            draw.line([tuple(point - lo) for point in points] + [tuple(points[0] - lo)], fill=color, width=1)
        crop = crop.resize((crop.width * 2, crop.height * 2))
        crop.save(args.output / (route + '-hull.png'))
        Image.fromarray(observed).save(args.output / (route + '-observed-mask.png'))
    result_path = args.output / 'fit.json'
    result_path.write_text(json.dumps(results, indent=2) + '\n', encoding='ascii')
    print(json.dumps(results))


if __name__ == '__main__':
    main()
