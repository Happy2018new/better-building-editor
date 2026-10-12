"""Describe preserved LOW cube/window controls without deriving UV or transfer."""
import argparse
import json
from pathlib import Path

import numpy as np

from analyze_liquid_workspace import capture_failures
from camera_projection import project_points
from capture_pure_liquid_native_controls import fixed_viewport
from liquid_coordinate_markers import checked_capture_image, fingerprint, write
from liquid_static_coordinate_epochs import check
from measure_native_liquid_side_uv import bilinear, side_grid


def project(world, camera, size, fov):
    engine = camera['stable']['screen']
    values = project_points(world.tolist(), camera['position'], camera['target'], engine, fov)
    if not all(row['isInScreen'] and row['depth'] > .05 for row in values):
        raise ValueError('Opaque witness geometric sample leaves the native viewport')
    return np.asarray([[row['screenX'] * size[0] / engine[0],
                        row['screenY'] * size[1] / engine[1]] for row in values])


def clearance(points, corners):
    distances = []
    signs = []
    for start, end in zip(corners, np.roll(corners, -1, axis=0)):
        edge = end - start
        relative = points - start
        cross = edge[0] * relative[:, 1] - edge[1] * relative[:, 0]
        signs.append(cross)
        fraction = np.clip(relative.dot(edge) / edge.dot(edge), 0., 1.)
        distances.append(np.linalg.norm(relative - fraction[:, None] * edge, axis=1))
    signs = np.asarray(signs)
    if not np.all(np.all(signs >= 0., axis=0) | np.all(signs <= 0., axis=0)):
        raise ValueError('A native interpolation footprint leaves the opaque face')
    return float(np.min(distances))


def audit(plan_path, native_path, output):
    if output.exists():
        raise ValueError('Choose a fresh LOW control audit output')
    plan = json.loads(plan_path.read_bytes())
    check(plan)
    native = json.loads(native_path.read_bytes())
    if (native['static_epoch'] != 'low' or native['static_coordinate_plan'] != fingerprint(plan_path)
            or native['opaque_cube_surfaces'] != plan['cube_surfaces']
            or native['opaque_cube_alias'] != plan['cube_alias_override']):
        raise ValueError('LOW input differs from the exact opaque-witness experiment')
    calibration_ref = native['calibration']
    if fingerprint(calibration_ref['path'])['sha256'] != calibration_ref['sha256']:
        raise ValueError('Camera calibration changed')
    calibration = json.loads(Path(calibration_ref['path']).read_bytes())
    if not all(calibration.get(key) for key in ('passed', 'completed', 'restored')):
        raise ValueError('Independent camera calibration did not pass and restore')
    captured = [(row['case'] + '/' + name, item['capture'])
                for row in native['cases'] for name, item in row['controls'].items()
                if item.get('capture')]
    provenance = capture_failures({label: row['capture'] for label, row in captured}, native['session_binding'])
    if provenance:
        raise ValueError('Saved native capture provenance failed: ' + repr(provenance))
    grids = {}
    for surface in plan['cube_surfaces']:
        grid = side_grid(surface['cell_origin'], surface['corner_heights'], surface['side'],
                         plan['cube_sample_grid']['u'], plan['cube_sample_grid']['vertical_fraction'])
        if surface['corner_heights'] != [1.] * 4:
            raise ValueError('LOW opaque audit requires the declared native unit cube')
        offsets = (((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)) if surface['side'] == 'north'
                   else ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0)))
        corners = np.asarray(surface['cell_origin'], float) + np.asarray(offsets, float)
        grids[surface['side']] = (grid['world_points'], corners)
    reference, rows = {}, []
    for label, record in captured:
        capture = record['capture']
        fixed_viewport(record, native['camera'])
        if record['camera_before'] != record['camera_after']:
            raise ValueError('Camera changed during a LOW control capture')
        faces = {}
        with checked_capture_image(record) as image:
            pixels = np.asarray(image, float)
        for side, (world, corners) in grids.items():
            xy = project(world, native['camera'], record['size'], calibration['vertical_fov'])
            face_corners = project(corners, native['camera'], record['size'], calibration['vertical_fov'])
            neighbors = np.floor(xy).astype(int)[:, None, :] + np.array(((0, 0), (1, 0), (0, 1), (1, 1)))
            minimum_clearance = clearance(neighbors.reshape(-1, 2) + .5, face_corners)
            observed = bilinear(pixels, xy[:, 0], xy[:, 1])
            if side not in reference:
                reference[side] = observed.copy()
            delta = observed - reference[side]
            faces[side] = {'sample_count': len(observed), 'mean_rgb': np.mean(observed, axis=0).tolist(),
                'minimum_native_footprint_boundary_clearance_pixels': minimum_clearance,
                'first_control_delta_rgb_rmse': float(np.sqrt(np.mean(delta ** 2))),
                'first_control_maximum_absolute_rgb_delta': float(np.max(np.abs(delta)))}
        rows.append({'label': label, 'png': fingerprint(record['path']), 'window': capture['window'],
            'frame': capture['frame'], 'foreground_unchanged': capture['foreground_unchanged'],
            'cube_constant_low_faces': faces})
    session = json.loads(Path(native['session_file']).read_bytes())
    result = {'schema': 1, 'plan': fingerprint(plan_path), 'native_report': fingerprint(native_path),
        'calibration': calibration_ref, 'nominal_independent_vertical_fov': calibration['vertical_fov'],
        'startup_windows': session['noactivation']['windows'], 'saved_capture_window_observations': rows,
        'all_saved_capture_windows_not_minimized': all(not row['window']['minimized'] for row in rows),
        'all_saved_captures_fresh': all(row['frame']['frame_qpc_100ns'] > row['frame']['request_qpc_100ns'] for row in rows),
        'available_capture_provenance_passed': True,
        'scope': 'Read-only saved LOW controls at the independently calibrated nominal camera; no time/UV/source-region/filter fit',
        'limits': 'Window state is known only at startup and eight saved captures, not at the later binding failure. Constant LOW can test visible opaque-witness stability but lacks HIGH transfer and distinguishing coordinate/complement labels. Boundary clearance is nominal only; all-FOV review is separate.',
        'cube_sampling_accepted': False, 'native_uv_accepted': False, 'production_accepted': False}
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'native', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.plan.resolve(), args.native.resolve(), args.output.resolve())
    print(json.dumps({key: result[key] for key in ('all_saved_capture_windows_not_minimized',
        'all_saved_captures_fresh', 'available_capture_provenance_passed', 'native_uv_accepted',
        'production_accepted')}))
