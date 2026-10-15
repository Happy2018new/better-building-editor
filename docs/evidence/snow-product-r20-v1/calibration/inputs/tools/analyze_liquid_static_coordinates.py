"""Score static water UVs against candidate-independent flat native references."""
import argparse
import json
from pathlib import Path

import numpy as np

from analyze_liquid_workspace import capture_failures
from camera_projection import project_points
from capture_frozen_liquid_controls import native_gate
from capture_pure_liquid_native_controls import fixed_viewport
from diagnose_liquid_coordinate_sampling import nearest_templates
from liquid_coordinate_markers import checked_capture_image, fingerprint, hypotheses, validate_sequences, write
from liquid_static_coordinate_epochs import LOW, HIGH, check, frame
from measure_native_liquid_side_uv import FACE_CORNERS, bilinear, oriented_uv, side_grid, spatial_templates


def pixel_plane_grid(pixel_points, surface, camera, size, fov):
    """Intersect fixed raster pixel centers with the independently declared side plane."""
    position = np.asarray(camera['position'], float)
    if abs(camera.get('rotation', [0., 0., 0.])[2]) > .0001:
        raise ValueError('Frozen plane projection requires a zero-roll camera')
    forward = np.asarray(camera['target'], float)-position
    forward /= np.linalg.norm(forward)
    right = np.array((-forward[2], 0., forward[0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    engine = np.asarray(camera['stable']['screen'], float)
    edge_points = (np.asarray(pixel_points, float)+.5)*engine/np.asarray(size, float)
    focal = engine[1]/(2*np.tan(np.radians(fov)/2))
    directions = (forward[None, :] + (edge_points[:, 0]-engine[0]/2)[:, None]*right/focal
                  - (edge_points[:, 1]-engine[1]/2)[:, None]*up/focal)
    axis = 2 if surface['side'] == 'north' else 0
    origin = np.asarray(surface['cell_origin'], float)
    distance = (origin[axis]-position[axis])/directions[:, axis]
    world = position+distance[:, None]*directions
    u = world[:, 0]-origin[0] if surface['side'] == 'north' else 1-(world[:, 2]-origin[2])
    height = world[:, 1]-origin[1]
    first, second = FACE_CORNERS[surface['side']]
    heights = surface['corner_heights']
    top = heights[first]*(1-u)+heights[second]*u
    return {'u': u, 'height': height, 'top': top}


def texel_edges(grid, hypothesis):
    u, height, top = (np.asarray(grid[name], float) for name in ('u', 'height', 'top'))
    v = height if hypothesis.side_v == 'top' else 1-height/top if hypothesis.side_v == 'stretch' else 1-height
    x, y = oriented_uv(u, v, hypothesis.orientation)
    span = 32. if hypothesis.region == 'full' else 16.
    offset = np.array((span if hypothesis.region in ('ne', 'se') else 0.,
                       span if hypothesis.region in ('sw', 'se') else 0.))
    scale = span if hypothesis.pixel_mapping == 'edges' else span-1.
    return np.column_stack((x, y))*scale+offset+(.5 if hypothesis.pixel_mapping == 'centers' else 0.)


def samples(path, plan):
    source = json.loads(path.read_bytes())
    epoch = source['static_epoch']
    if (source['static_epoch_asset'] != plan['assets'][epoch]
            or source['phase_independent_strip'] != {'dimensions': [32, 1024],
                                                    'identical_square_frames': 32, 'opaque_alpha': True}):
        raise ValueError('Native epoch asset or frame identity differs from frozen plan')
    if source['static_coordinate_plan']['sha256'] != fingerprint(plan['_path'])['sha256']:
        raise ValueError('Epoch references a different immutable experiment')
    if (not source['completed'] or not source['restored'] or source['cleanup_errors']
            or not source['background_only']):
        raise ValueError('Native epoch did not complete and restore in background')
    calibration_ref = source['calibration']
    if fingerprint(calibration_ref['path'])['sha256'] != calibration_ref['sha256']:
        raise ValueError('Independent camera reference changed')
    calibration = json.loads(Path(calibration_ref['path']).read_bytes())
    if (not all(calibration.get(key) for key in ('completed', 'passed', 'restored'))
            or calibration['cleanup_errors'] or calibration['session_file'] != source['session_file']):
        raise ValueError('Epoch needs a passed same-session independent stone calibration')
    if [row['case'] for row in source['cases']] != [row['case'] for row in plan['geometry_sequences']]:
        raise ValueError('Epoch did not capture every declared geometry')
    captures, result = {}, []
    for row, geometry in zip(source['cases'], plan['geometry_sequences']):
        if row['source']['controls'] != geometry['controls'] or set(row['controls']) != set(plan['controls']):
            raise ValueError('Native geometry source or control set changed')
        images = {}
        for name, item in row['controls'].items():
            if not item['completed']:
                raise ValueError('A fixed native control is incomplete')
            record = item['capture']
            captures[row['case'] + '/' + name] = record['capture']
            fixed_viewport(record, source['camera'])
            gate = native_gate(item['native_before_capture'], item['native_after_capture'], row['source'],
                               row['source']['controls'][name]['cells'])
            if not gate['public_snapshot_unchanged']:
                raise ValueError('Native source or neighborhood changed during capture')
            with checked_capture_image(record) as image:
                images[name] = np.asarray(image, float)
        for side in ('north', 'west'):
            arrays = {name: [] for name in ('u', 'height', 'top', 'world_points')}
            observations = {name: [] for name in plan['controls']}
            points, native_grids, quad_grids, weights, native_observations = [], [], [], [], []
            for surface in geometry['surfaces']:
                if surface['side'] != side:
                    continue
                grid = side_grid(surface['cell_origin'], surface['corner_heights'], side,
                                 plan['sample_grid']['u'], plan['sample_grid']['vertical_fraction'])
                camera = source['camera']
                engine = camera['stable']['screen']
                size = row['controls'][plan['sample_control']]['capture']['size']

                def project(world):
                    values = project_points(world.tolist(), camera['position'], camera['target'],
                                            engine, calibration['vertical_fov'])
                    if not all(item['isInScreen'] and item['depth'] > .05 for item in values):
                        raise ValueError('Frozen geometry point leaves the native camera')
                    return np.asarray([[p['screenX']*size[0]/engine[0], p['screenY']*size[1]/engine[1]]
                                       for p in values])

                xy = project(grid['world_points'])
                lower = np.floor(xy).astype(int)
                neighbors = lower[:, None, :]+np.array(((0, 0), (1, 0), (0, 1), (1, 1)))[None, :, :]
                fraction = xy-lower
                fx, fy = fraction[:, 0], fraction[:, 1]
                weights.extend(np.column_stack(((1-fx)*(1-fy), fx*(1-fy), (1-fx)*fy, fx*fy)).tolist())
                flat = neighbors.reshape(-1, 2)
                native_grids.append(pixel_plane_grid(flat, surface, camera, size, calibration['vertical_fov']))
                left = flat.copy()
                left[:, 0] = np.floor_divide(flat[:, 0], 2)*2
                right = left+np.array((1, 0))
                bottom = flat.copy()
                bottom[:, 1] = size[1]-1-np.floor_divide(size[1]-1-flat[:, 1], 2)*2
                top = bottom-np.array((0, 1))
                quad_grids.append([pixel_plane_grid(points, surface, camera, size, calibration['vertical_fov'])
                                   for points in (left, right, bottom, top)])
                native_observations.append({name: image[flat[:, 1], flat[:, 0]].reshape(-1, 4, 3).tolist()
                                            for name, image in images.items()})
                for name in observations:
                    observations[name].extend(bilinear(images[name], xy[:, 0], xy[:, 1]).tolist())
                for name in arrays:
                    arrays[name].extend(grid[name].tolist())
                points.extend(xy.tolist())
            depth = row['case'].split('_depth_')[1].split('_')[0]
            result.append({'id': depth + '/' + side, 'role': plan['geometry_roles'][depth], 'grid': arrays,
                'observations': observations, 'native_sample_points': points,
                'native_grid': {name: np.concatenate([grid[name] for grid in native_grids]).tolist()
                                for name in ('u', 'height', 'top')},
                'quad_grids': [{name: np.concatenate([grids[index][name] for grids in quad_grids]).tolist()
                               for name in ('u', 'height', 'top')} for index in range(4)],
                'native_observations': {name: np.concatenate([row[name] for row in native_observations]).tolist()
                                        for name in plan['controls']},
                'host_bilinear_weights': weights, 'calibration_fov': calibration['vertical_fov'],
                'camera': source['camera'], 'native_size': size})
    failures = capture_failures(captures, source['session_binding'])
    if failures:
        raise ValueError('Native capture provenance failed: ' + repr(failures))
    validate_sequences(result)
    return result


def texel_aa_templates(pixels, sequence, hypothesis):
    q = texel_edges(sequence['native_grid'], hypothesis)
    left, right, bottom, top = (texel_edges(grid, hypothesis) for grid in sequence['quad_grids'])
    screen_derivatives = np.stack((right-left, top-bottom), axis=2)
    lengths = np.linalg.norm(screen_derivatives, axis=2)
    sharpening = np.maximum(1/np.maximum(lengths, 1e-12), 1.)
    fraction = q-np.floor(q)
    first = np.clip(fraction*sharpening, 0., .5)
    second = np.clip((fraction-1)*sharpening+.5, 0., .5)
    warped = first+second
    footprint = np.maximum(np.linalg.norm(screen_derivatives[:, :, 0], axis=1),
                           np.linalg.norm(screen_derivatives[:, :, 1], axis=1))
    lod = np.log2(2*np.maximum(footprint, 1e-12))
    reverse = np.clip((lod-2)/(-3), 0., 1.)
    weight = reverse*reverse*(3-2*reverse)
    adjusted = q*(1-weight[:, None])+(np.floor(q)+warped)*weight[:, None]-.5
    return bilinear(pixels[:, :, :3].astype(float), adjusted[:, 0], adjusted[:, 1])


def measure(epochs, plan):
    identifiers = [row['id'] for row in epochs['low']]
    if any([row['id'] for row in rows] != identifiers for rows in epochs.values()):
        raise ValueError('Static epoch sequence identities differ')
    limits = plan['limits']
    prepared, stability = [], {}
    for index, reference in enumerate(epochs['low']):
        low = np.asarray(reference['native_observations'][plan['sample_control']], float)
        high = np.asarray(epochs['high'][index]['native_observations'][plan['sample_control']], float)
        coordinate = np.asarray(epochs['coordinate'][index]['observations'][plan['sample_control']], float)
        complement = np.asarray(epochs['complement'][index]['observations'][plan['sample_control']], float)
        spread = high-low
        backgrounds = []
        for epoch, rows in epochs.items():
            for control in ('supported_negative', 'empty'):
                a = np.asarray(rows[index]['observations'][control], float)
                b = np.asarray(reference['observations'][control], float)
                backgrounds.append(float(np.sqrt(np.mean((a-b)**2))))
        weights = np.asarray(reference['host_bilinear_weights'], float)[:, :, None]
        sampled_sum = np.sum((low+high)*weights, axis=1)
        complement_error = float(np.sqrt(np.mean((coordinate+complement-sampled_sum)**2)))
        identical_camera = all(row[index]['camera'] == reference['camera'] and
                               row[index]['native_size'] == reference['native_size'] and
                               row[index]['calibration_fov'] == reference['calibration_fov'] for row in epochs.values())
        minimum = spread.reshape(-1, 3).min(axis=0)
        stability[reference['id']] = {'minimum_reference_spread': minimum.tolist(),
            'maximum_dry_control_rmse': max(backgrounds), 'complement_native_rgb_rmse': complement_error,
            'exact_camera_viewport_fov_identity': identical_camera,
            'passed': bool(np.min(minimum[1:]) >= limits['minimum_green_blue_reference_spread']
                and minimum[0] >= limits['minimum_red_reference_spread'] and max(backgrounds) <= limits['maximum_dry_control_rmse']
                and complement_error <= limits['maximum_complement_source_rmse'] and identical_camera)}
        prepared.append((reference, low, spread, np.stack((coordinate, complement))))
    candidates = []
    for sampler in ('bilinear', 'nearest', 'native_texel_aa'):
        for hypothesis in hypotheses():
            rows = {}
            for sequence, low, spread, observed in prepared:
                pixels = frame('coordinate')
                grid = {name: np.asarray(sequence['native_grid'][name], float) for name in ('u', 'height', 'top')}
                if sampler == 'native_texel_aa':
                    expected = texel_aa_templates(pixels, sequence, hypothesis)
                elif sampler == 'nearest':
                    expected = nearest_templates(pixels, grid, hypothesis)
                else:
                    expected = spatial_templates(pixels[None, :, :, :3].astype(float), grid, hypothesis)[0]
                expected = expected.reshape(-1, 4, 3)
                weights = np.asarray(sequence['host_bilinear_weights'], float)[:, :, None]
                primary = np.sum((low+(expected-LOW)/(HIGH-LOW)*spread)*weights, axis=1)
                secondary = np.sum((low+(HIGH-expected)/(HIGH-LOW)*spread)*weights, axis=1)
                predicted = np.stack((primary, secondary))
                residual = np.mean((observed-predicted)**2)
                null = np.sum((low+.5*spread)*weights, axis=1)
                null_variance = np.mean((observed-null[None, :, :])**2)
                texture_rms = float(np.sqrt(np.mean((predicted-null[None, :, :])**2)))
                row = {'rgb_rmse': float(np.sqrt(residual)), 'explained_variance': float(1-residual/max(null_variance, 1e-12)),
                       'texture_rms': texture_rms}
                row['passed'] = (row['rgb_rmse'] <= limits['maximum_rgb_rmse']
                    and row['explained_variance'] >= limits['minimum_explained_variance']
                    and texture_rms >= limits['minimum_texture_rms'])
                rows[sequence['id']] = row
            score = float(np.mean([rows[sequence['id']]['rgb_rmse'] for sequence, *_ in prepared if sequence['role'] == 'training']))
            candidates.append((score, sampler, hypothesis, rows))
    candidates.sort(key=lambda row: row[0])
    error, sampler, selected, rows = candidates[0]
    identification = {}
    for prop in ('region', 'v_basis', 'pixel_mapping'):
        alternatives = [row for row in candidates if getattr(row[2], prop) != getattr(selected, prop)]
        margin = min(row[0] for row in alternatives)-error
        holdout_rejected = all(any(not row[3][sequence['id']]['passed'] for sequence, *_ in prepared
                                  if sequence['role'] == 'holdout') for row in alternatives)
        identification[prop] = {'training_margin_rgb_rmse': margin, 'every_alternative_holdout_rejected': holdout_rejected,
            'identified': margin >= limits['minimum_property_margin_rmse'] and holdout_rejected}
    passed = all(row['passed'] for row in rows.values()) and all(row['passed'] for row in stability.values())
    return {'schema': 1, 'selected': selected.__dict__, 'sampler': sampler, 'training_rgb_rmse': error,
        'sequences': rows, 'stability': stability, 'identification': identification, 'limits': limits,
        'native_side_uv_observed': passed and all(row['identified'] for row in identification.values()),
        'native_uv_accepted': False, 'production_accepted': False,
        'scope': 'Static side UV/source-filtering only; no animation, top UV or production acceptance',
        'photometry': 'Candidate-independent per-pixel low/high native references; no candidate gain, shift or phase fitted'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--input', type=Path, nargs=4, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh output path')
    plan = json.loads(args.plan.read_bytes())
    check(plan)
    plan['_path'] = str(args.plan.resolve())
    epochs = {}
    for path in args.input:
        epoch = json.loads(path.read_bytes())['static_epoch']
        if epoch in epochs:
            raise ValueError('Duplicate immutable epoch')
        epochs[epoch] = samples(path, plan)
    if set(epochs) != set(plan['epochs']):
        raise ValueError('All four immutable static epochs are required')
    report = measure(epochs, plan)
    report.update(plan=fingerprint(args.plan), inputs=[fingerprint(path) for path in args.input], sampled_epochs=epochs)
    write(args.output, report)
    print(json.dumps({key: report[key] for key in ('selected', 'sampler', 'training_rgb_rmse', 'native_side_uv_observed', 'identification')}))


if __name__ == '__main__':
    main()
