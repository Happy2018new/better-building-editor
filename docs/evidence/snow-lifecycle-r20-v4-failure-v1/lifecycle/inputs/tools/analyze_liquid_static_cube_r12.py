"""Score canonical opaque cube D4/filter candidates with within-epoch controls."""
import argparse
from copy import deepcopy
import json
from pathlib import Path

import numpy as np

import analyze_liquid_static_coordinates as static
from liquid_coordinate_markers import fingerprint, hypotheses, write
from liquid_static_coordinate_epochs import HIGH, LOW, check, frame
from measure_native_liquid_side_uv import spatial_templates
from diagnose_liquid_coordinate_sampling import nearest_templates


def cube_stability(epochs, limits):
    result = {}
    for index, reference in enumerate(epochs['low']):
        low = np.asarray(reference['native_observations']['supported_positive'], float)
        high = np.asarray(epochs['high'][index]['native_observations']['supported_positive'], float)
        coordinate = np.asarray(epochs['coordinate'][index]['observations']['supported_positive'], float)
        complement = np.asarray(epochs['complement'][index]['observations']['supported_positive'], float)
        weights = np.asarray(reference['host_bilinear_weights'], float)[:, :, None]
        minimum = (high - low).reshape(-1, 3).min(axis=0)
        deviations = [float(np.sqrt(np.mean((np.asarray(row[index]['native_observations'][name], float)
                       - np.asarray(row[index]['native_observations']['supported_positive'], float)) ** 2)))
                      for row in epochs.values() for name in ('supported_negative', 'liquid_only', 'empty')]
        sum_error = float(np.sqrt(np.mean((coordinate + complement - np.sum((low + high) * weights, axis=1)) ** 2)))
        same_camera = all(rows[index]['camera'] == reference['camera']
                          and rows[index]['native_size'] == reference['native_size']
                          and rows[index]['calibration_fov'] == reference['calibration_fov']
                          for rows in epochs.values())
        result[reference['id']] = {'minimum_reference_spread': minimum.tolist(),
            'maximum_within_epoch_control_native_rgb_rmse': max(deviations),
            'complement_native_rgb_rmse': sum_error, 'exact_camera_viewport_fov_identity': same_camera,
            'passed': bool(np.min(minimum[1:]) >= limits['minimum_green_blue_reference_spread']
                and minimum[0] >= limits['minimum_red_reference_spread']
                and max(deviations) <= limits['maximum_dry_control_rmse']
                and sum_error <= limits['maximum_complement_source_rmse'] and same_camera)}
    return result


def measure_cube(epochs, plan):
    identifiers = [row['id'] for row in epochs['low']]
    if any([row['id'] for row in rows] != identifiers for rows in epochs.values()):
        raise ValueError('Cube epoch sequence identities differ')
    limits = plan['limits']
    stability = cube_stability(epochs, limits)
    candidates = []
    for sampler in ('bilinear', 'nearest', 'native_texel_aa'):
        for hypothesis in (row for row in hypotheses() if row.side_v == 'bottom'):
            scores = {}
            for index, sequence in enumerate(epochs['low']):
                low = np.asarray(sequence['native_observations']['supported_positive'], float)
                spread = np.asarray(epochs['high'][index]['native_observations']['supported_positive'], float) - low
                observed = np.stack([epochs[epoch][index]['observations']['supported_positive']
                                     for epoch in ('coordinate', 'complement')])
                pixels = frame('coordinate')
                grid = {name: np.asarray(sequence['native_grid'][name], float) for name in ('u', 'height', 'top')}
                if sampler == 'native_texel_aa':
                    expected = static.texel_aa_templates(pixels, sequence, hypothesis)
                elif sampler == 'nearest':
                    expected = nearest_templates(pixels, grid, hypothesis)
                else:
                    expected = spatial_templates(pixels[None, :, :, :3].astype(float), grid, hypothesis)[0]
                expected = expected.reshape(-1, 4, 3)
                weights = np.asarray(sequence['host_bilinear_weights'], float)[:, :, None]
                primary = np.sum((low + (expected - LOW) / (HIGH - LOW) * spread) * weights, axis=1)
                secondary = np.sum((low + (HIGH - expected) / (HIGH - LOW) * spread) * weights, axis=1)
                predicted = np.stack((primary, secondary))
                residual = np.mean((observed - predicted) ** 2)
                null = np.sum((low + .5 * spread) * weights, axis=1)
                null_variance = np.mean((observed - null[None, :, :]) ** 2)
                texture_rms = float(np.sqrt(np.mean((predicted - null[None, :, :]) ** 2)))
                score = {'rgb_rmse': float(np.sqrt(residual)),
                    'explained_variance': float(1 - residual / max(null_variance, 1e-12)), 'texture_rms': texture_rms}
                score['passed'] = (score['rgb_rmse'] <= limits['maximum_rgb_rmse']
                    and score['explained_variance'] >= limits['minimum_explained_variance']
                    and texture_rms >= limits['minimum_texture_rms'])
                scores[sequence['id']] = score
            training = float(np.mean([scores[row['id']]['rgb_rmse'] for row in epochs['low'] if row['role'] == 'training']))
            candidates.append((training, sampler, hypothesis, scores))
    candidates.sort(key=lambda row: row[0])
    error, sampler, selected, scores = candidates[0]
    identification = {}
    for prop in ('region', 'pixel_mapping', 'orientation', 'sampler'):
        alternatives = [row for row in candidates if
                        (row[1] != sampler if prop == 'sampler' else getattr(row[2], prop) != getattr(selected, prop))]
        margin = min(row[0] for row in alternatives) - error
        rejected = all(any(not row[3][sequence['id']]['passed'] for sequence in epochs['low']
                           if sequence['role'] == 'holdout') for row in alternatives)
        identification[prop] = {'training_margin_rgb_rmse': margin,
            'every_alternative_holdout_rejected': rejected,
            'identified': margin >= limits['minimum_property_margin_rmse'] and rejected}
    spatial = (all(row['passed'] for row in scores.values()) and all(row['passed'] for row in stability.values())
               and all(row['identified'] for row in identification.values()))
    return {'selected': selected.__dict__, 'sampler': sampler, 'training_rgb_rmse': error,
        'sequences': scores, 'stability': stability, 'identification': identification, 'limits': limits,
        'cube_spatial_candidate_observed': spatial,
        'canonical_v_basis': 'bottom only; top with D4 flip_y and bottom/stretch are equivalent for a unit cube',
        'photometry': 'Per-native-pixel opaque cube LOW/HIGH references; within-epoch all-control stability; no candidate transfer fitted',
        'candidate_count': len(candidates), 'native_uv_accepted': False, 'production_accepted': False}


def analyze(plan_path, paths, output):
    if output.exists():
        raise ValueError('Choose a fresh R12 same-alias analysis output')
    plan = json.loads(plan_path.read_bytes())
    check(plan)
    plan['_path'] = str(plan_path.resolve())
    cube_plan = deepcopy(plan)
    cube_plan['sample_grid'] = plan['cube_sample_grid']
    for row in cube_plan['geometry_sequences']:
        row['surfaces'] = plan['cube_surfaces']
    water, cube = {}, {}
    for path in paths:
        native = json.loads(path.read_bytes())
        if native['opaque_cube_alias'] != plan['cube_alias_override'] or native['opaque_cube_surfaces'] != plan['cube_surfaces']:
            raise ValueError('Cube geometry/alias differs from the immutable R12 input')
        health_ref = native['runtime_health_before_fixture']
        if fingerprint(health_ref['path']) != health_ref:
            raise ValueError('Runtime health evidence bytes changed')
        health = json.loads(Path(health_ref['path']).read_bytes())
        if not all(health.get(key) for key in ('passed', 'completed', 'binding_verified', 'timer_cleanup_verified')):
            raise ValueError('Runtime did not pass before the fixture')
        if health['session_file'] != native['session_file'] or health['owner'] != native['owner']:
            raise ValueError('Runtime health belongs to another owner/session')
        epoch = native['static_epoch']
        if epoch in water:
            raise ValueError('Duplicate immutable epoch')
        water[epoch], cube[epoch] = static.samples(path, plan), static.samples(path, cube_plan)
    if set(water) != set(plan['epochs']):
        raise ValueError('All four immutable R12 epochs are required')
    faces = {side: measure_cube({epoch: [row for row in rows if row['id'].endswith('/' + side)]
                                for epoch, rows in cube.items()}, cube_plan) for side in ('north', 'west')}
    shared = (all(row['cube_spatial_candidate_observed'] for row in faces.values())
              and len({(row['selected']['region'], row['selected']['pixel_mapping'], row['sampler'])
                       for row in faces.values()}) == 1)
    result = {'schema': 2, 'plan': fingerprint(plan_path), 'inputs': [fingerprint(path) for path in paths],
        'water': static.measure(water, plan), 'cube_faces': faces, 'cube_shared_spatial_candidate_observed': shared,
        'sampled_water_epochs': water, 'sampled_cube_epochs': cube,
        'native_uv_accepted': False, 'production_accepted': False,
        'scope': 'Predeclared independent opaque cube D4/filter and guarded water candidates; all-FOV audit remains separate'}
    write(output, result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', type=Path, required=True)
    parser.add_argument('--input', type=Path, nargs=4, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.plan.resolve(), args.input, args.output.resolve())
    print(json.dumps({'cube_shared_spatial_candidate_observed': result['cube_shared_spatial_candidate_observed'],
                      'water_observed': result['water']['native_side_uv_observed']}))
