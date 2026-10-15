"""Measure both translating glint layers in source UVs from verified native frames."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.optimize import differential_evolution, least_squares

from analyze_item_dense_motion_r17 import verified_json
from analyze_item_sprite_product import ROOT, item_polygons, project_editor
from camera_projection import project_points
from item_sprite_capture_contract import camera_matches, snapshot_digest

LIMITS = {'maximum_fit_nrmse': .15, 'maximum_direction_error_degrees': 15.,
          'minimum_speed_ratio': .8, 'maximum_speed_ratio': 1.25,
          'minimum_glint_gain_ratio': .8, 'maximum_glint_gain_ratio': 1.25,
          'minimum_duration_seconds': 7., 'maximum_frame_gap_seconds': .25}


def sample_texture(texture, coordinates):
    coordinates = np.remainder(coordinates, 1.) * len(texture) - .5
    left = np.floor(coordinates).astype(int)
    fraction = coordinates - left
    return texture[left % len(texture)] * (1. - fraction) + texture[(left + 1) % len(texture)] * fraction


def model(parameters, uv, times, texture):
    first = uv @ parameters[:2]
    second = uv @ parameters[4:6]
    return (sample_texture(texture, first[None] + times[:, None] * parameters[2] + parameters[3]) +
            sample_texture(texture, second[None] + times[:, None] * parameters[6] + parameters[7])) ** 2


def residual(parameters, uv, times, observed, texture):
    predicted = model(parameters, uv, times, texture)
    predicted -= predicted.mean(axis=0)
    gain = max(0., float((predicted * observed).sum() / max(1e-12, (predicted * predicted).sum())))
    return predicted * gain - observed


def layers(parameters):
    result = []
    for offset in (0, 4):
        wave = np.asarray(parameters[offset:offset + 2])
        rate = float(parameters[offset + 2])
        velocity = -rate * wave / np.dot(wave, wave)
        result.append({'wave_vector': wave.tolist(), 'texture_cycles_per_second': rate,
            'uv_scale': float(np.linalg.norm(wave)),
            'wave_angle_degrees': float(np.degrees(np.arctan2(wave[1], wave[0]))),
            'phase_velocity_uv_per_second': velocity.tolist(),
            'phase_speed_uv_per_second': float(np.linalg.norm(velocity)),
            'motion_angle_degrees': float(np.degrees(np.arctan2(velocity[1], velocity[0])))})
    return result


def direction_comparison(product, reference):
    candidates = []
    for order in itertools.permutations(range(2)):
        rows = []
        for first, index in zip(product, order):
            second = reference[index]
            angle = abs((first['motion_angle_degrees'] - second['motion_angle_degrees'] + 180.) % 360. - 180.)
            ratio = first['phase_speed_uv_per_second'] / second['phase_speed_uv_per_second']
            rows.append({'direction_error_degrees': angle, 'speed_ratio': ratio,
                'passed': angle <= LIMITS['maximum_direction_error_degrees'] and
                LIMITS['minimum_speed_ratio'] <= ratio <= LIMITS['maximum_speed_ratio']})
        candidates.append({'reference_layer_order': list(order), 'layers': rows,
                           'passed': all(row['passed'] for row in rows)})
    return min(candidates, key=lambda row: sum(item['direction_error_degrees'] +
        30. * abs(np.log(item['speed_ratio'])) for item in row['layers']))


def brightness_comparison(product, reference):
    if not product.get('fit_valid') or not reference.get('fit_valid'):
        return {'passed': False, 'status': 'NO_VALID_TEXTURE_FIT'}
    ratios = np.asarray(product['rgb_temporal_gains'][:2]) / reference['rgb_temporal_gains'][:2]
    return {'red_green_gain_product_over_native': ratios.tolist(),
            'passed': bool(np.all(ratios >= LIMITS['minimum_glint_gain_ratio']) and
                           np.all(ratios <= LIMITS['maximum_glint_gain_ratio'])),
            'scope': 'Red/green dynamic additive amplitude; blue can saturate and static base is excluded'}


def fit(samples, texture, global_search=False):
    uv, times = samples['uv'] - .5, samples['times']
    observed = samples['samples'][:, :, 0].astype(float)
    observed -= observed.mean(axis=0)
    eligible = np.ptp(observed, axis=0) > 8.
    uv, observed = uv[eligible], observed[:, eligible]
    if len(uv) < 24:
        raise ValueError('Too few independently visible glint samples')
    selected_times = np.unique(np.linspace(0, len(times) - 1, min(65, len(times))).astype(int))
    selected_uv = np.unique(np.linspace(0, len(uv) - 1, min(70, len(uv))).astype(int))
    train_uv, train_times = uv[selected_uv], times[selected_times]
    train_observed = observed[np.ix_(selected_times, selected_uv)]
    train_observed -= train_observed.mean(axis=0)
    bounds = ([-1.5, -1.5, .01, -2., -1.5, -1.5, -.6, -2.],
              [1.5, 1.5, .6, 2., 1.5, 1.5, -.01, 2.])
    starts = [np.array((.08663, .492, .13325, .1662, .47008, -.17103, -.3636, .2062)),
              np.array((.4330127, .25, .2, .25, .4330127, -.25, -.1, .75))]
    objective = lambda p: residual(p, train_uv, train_times, train_observed, texture).ravel()
    for start in tuple(starts):
        def phase_objective(phases):
            point = start.copy()
            point[[3, 7]] = phases
            return float(np.mean(objective(point) ** 2))
        for seed in (17, 43):
            phase = differential_evolution(phase_objective, [(0., 1.), (0., 1.)],
                seed=seed, maxiter=100, popsize=10, tol=1e-7, polish=True)
            point = start.copy()
            point[[3, 7]] = phase.x
            starts.append(point)
    candidates = [least_squares(objective, start, bounds=bounds, max_nfev=350) for start in starts]
    if global_search:
        search = differential_evolution(lambda p: float(np.mean(objective(p) ** 2)),
            list(zip(*bounds)), seed=31, maxiter=600, popsize=10, tol=1e-7, polish=False)
        candidates.append(least_squares(objective, search.x, bounds=bounds, max_nfev=500))
    candidates.sort(key=lambda row: np.mean(row.fun ** 2))
    fitted = candidates[0]
    error = residual(fitted.x, uv, times, observed, texture)
    nrmse = float(np.sqrt(np.mean(error ** 2) / max(1e-12, np.mean(observed ** 2))))
    predicted = model(fitted.x, uv, times, texture)
    predicted -= predicted.mean(axis=0)
    colors = samples['samples'][:, eligible, :].astype(float)
    colors -= colors.mean(axis=0)
    gains = np.sum(predicted[:, :, None] * colors, axis=(0, 1)) / np.sum(predicted ** 2)
    return {'parameters': fitted.x.tolist(), 'layers': layers(fitted.x), 'nrmse': nrmse,
            'fit_valid': nrmse <= LIMITS['maximum_fit_nrmse'], 'uv_samples': len(uv),
            'frames': len(times), 'duration_seconds': float(times[-1] - times[0]),
            'training_uv_samples': len(train_uv), 'training_frames': len(train_times),
            'rgb_temporal_gains': gains.tolist(),
            'fit_scope': 'Positive-gain squared sum of the actual two native texture layers; temporal mean removes static base'}


def homography(corners):
    matrix, values = [], []
    for (u, v), (x, y) in zip(((0., 0.), (1., 0.), (1., 1.), (0., 1.)), corners):
        matrix.extend(((u, v, 1., 0., 0., 0., -x*u, -x*v),
                       (0., 0., 0., u, v, 1., -y*u, -y*v)))
        values.extend((x, y))
    return np.append(np.linalg.solve(matrix, values), 1.).reshape(3, 3)


def extract(report, route, texture, pose, output):
    closeup = report['closeup']
    rows = closeup['native_reference']['captures'] if route == 'native' else closeup['captures']
    row = next(item for item in rows if item['label'] == route + '_0')
    size = row['capture']['width'], row['capture']['height']
    position = tuple(closeup['fixture']['positions']['enchanted'])
    with Image.new('RGBA', (1, 1), (255, 255, 255, 255)) as plane:
        polygon = next(item_polygons(position, plane, pose))
    if route == 'editor':
        corners = project_editor(polygon, position, row['state'], size)
    else:
        world = next(item for item in closeup['captures'] if item['label'] == 'world_0')
        origin = world['state']['origin']
        polygon = [tuple(point[axis] + origin[axis] for axis in range(3)) for point in polygon]
        camera = row['camera_expected']
        if not camera_matches(camera, closeup['world_camera']):
            raise ValueError('Glint source camera differs from the declared native reference')
        corners = [(point['screenX'], point['screenY']) for point in project_points(polygon,
            camera['position'], camera['target'], size, report['camera_calibration']['vertical_fov'])]
    alpha = np.asarray(texture.convert('RGBA'))[:, :, 3]
    uv = np.array([((x + .5) / texture.width, (y + .5) / texture.height)
        for y in range(texture.height) for x in range(texture.width) if alpha[y, x] >= 128])
    transform = homography(corners)
    projected = transform @ np.vstack((uv.T, np.ones(len(uv))))
    xy = np.floor(projected[:2] / projected[2]).astype(int)
    if (xy < 0).any() or (xy[0] >= size[0]).any() or (xy[1] >= size[1]).any():
        raise ValueError('Glint UV samples extend outside the native viewport')
    sampled = np.linalg.inv(transform) @ np.vstack((xy + .5, np.ones(len(uv))))
    uv = (sampled[:2] / sampled[2]).T
    record = closeup['motion_bursts'][route]
    if not record['stable']:
        raise ValueError('Glint dense capture camera or layout drift')
    receipt = verified_json(Path(record['receipt']), record['sha256'])
    if not receipt['capture_valid'] or not receipt['temporal_complete']:
        raise ValueError('Glint dense receipt is incomplete')
    if receipt['instance']['game_identity'] != report['session']['game_identity']:
        raise ValueError('Glint capture came from another game instance')
    samples, times, pixel_sources = [], [], []
    folder = output / (route + '-frames')
    folder.mkdir()
    bounds = (int(xy[0].min()) - 2, int(xy[1].min()) - 2,
              int(xy[0].max()) + 3, int(xy[1].max()) + 3)
    for frame in receipt['frames']:
        if frame['png'] is None:
            continue
        raw = verified_json(Path(frame['receipt']['path']), frame['receipt']['sha256'])
        image_path = Path(frame['png']['path'])
        if hashlib.sha256(image_path.read_bytes()).hexdigest() != frame['png']['sha256']:
            raise ValueError('Glint dense image changed')
        times.append(raw['frame_qpc_100ns'] / 1e7)
        with Image.open(image_path) as image:
            samples.append(np.asarray(image.convert('RGB'))[xy[1], xy[0]])
            retained = folder / ('%04d.png' % len(samples))
            image.convert('RGB').crop(bounds).save(retained)
        pixel_sources.append({'full_frame_sha256': frame['png']['sha256'],
            'capture_receipt_sha256': frame['receipt']['sha256'],
            'frame_qpc_100ns': raw['frame_qpc_100ns'],
            'retained_crop': retained.relative_to(output).as_posix(),
            'retained_crop_sha256': hashlib.sha256(retained.read_bytes()).hexdigest()})
    times = np.asarray(times) - times[0]
    if (times[-1] < LIMITS['minimum_duration_seconds'] or (np.diff(times) <= 0.).any()
            or np.diff(times).max() > LIMITS['maximum_frame_gap_seconds']):
        raise ValueError('Glint measured frame cadence is insufficient')
    result = {'uv': uv, 'samples': np.asarray(samples), 'times': times, 'corners': np.asarray(corners)}
    np.savez_compressed(output / (route + '-samples.npz'), **result)
    (output / (route + '-pixel-sources.json')).write_text(json.dumps({
        'crop_bounds': bounds, 'sample_xy': xy.T.tolist(), 'frames': pixel_sources,
        'source_game_identity': report['session']['game_identity'],
        'dense_receipt_sha256': record['sha256']}, indent=2) + '\n', encoding='ascii')
    return result


def analyze(source, sparse_source, output, assets, global_search):
    report = json.loads(source.read_bytes())
    sparse = json.loads(sparse_source.read_bytes())
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if (sparse['source_sha256'] != source_hash or not report['completed'] or report['cleanup_errors']
            or not report['source_unchanged'] or report['launch_sources'] != report['sources_after']
            or snapshot_digest(report['launch_sources']) != report['launch_sources_sha256']
            or not sparse.get('native_closeup', {}).get('reference_valid')
            or sparse.get('capture_failures')):
        raise ValueError('Glint direction requires complete, restored, bound actual native evidence')
    output.mkdir(parents=True, exist_ok=False)
    catalog_path = assets / 'tools/data/item_icon_catalog_nemc_3.10.0.420447.json'
    catalog = json.loads(catalog_path.read_bytes())
    if hashlib.sha256(catalog_path.read_bytes()).hexdigest() != report['launch_sources'][catalog_path.relative_to(assets).as_posix()]:
        raise ValueError('Glint direction catalog differs from captured source')
    resource = next(row['resource'] for row in catalog['items'] if (row['name'], row['aux']) == ('minecraft:diamond_sword', 0))
    texture_path = assets / ('resource_pack/textures/models/modern_projection/item_icons/' + resource + '.png')
    glint_path = assets / 'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png'
    for path in (texture_path, glint_path):
        if hashlib.sha256(path.read_bytes()).hexdigest() != report['launch_sources'][path.relative_to(assets).as_posix()]:
            raise ValueError('Glint direction texture differs from captured source')
    with Image.open(glint_path) as image:
        glint = np.asarray(image.convert('RGB'))[:, :, 0].astype(float) / 255.
    if not np.all(glint == glint[0]):
        raise ValueError('This native one-dimensional texture model does not apply to the captured asset')
    results = {}
    with Image.open(texture_path) as texture:
        for route in ('native', 'world', 'world_missing', 'editor'):
            samples = extract(report, route, texture, catalog['pose'], output)
            try:
                results[route] = fit(samples, glint[0], global_search)
            except ValueError as error:
                if route == 'native':
                    raise
                results[route] = {'fit_valid': False, 'error': str(error), 'layers': []}
            print(json.dumps({'route': route, **results[route]}), flush=True)
            (output / 'partial.json').write_text(json.dumps(results, indent=2) + '\n', encoding='ascii')
    reference = results['native']
    comparisons = {route: (direction_comparison(row['layers'], reference['layers'])
                   if row['layers'] else {'passed': False, 'status': 'NO_MEASURABLE_GLINT'})
                   for route, row in results.items() if route != 'native'}
    brightness = {route: brightness_comparison(row, reference) for route, row in results.items()
                  if route != 'native'}
    reversed_reference = [dict(layer, motion_angle_degrees=layer['motion_angle_degrees'] + 180.)
                          for layer in reference['layers']]
    rotated_reference = [dict(layer, motion_angle_degrees=layer['motion_angle_degrees'] + 90.)
                         for layer in reference['layers']]
    negatives = {'time_reversed_rejected': not direction_comparison(reversed_reference, reference['layers'])['passed'],
                 'wrong_uv_rotation_rejected': not direction_comparison(rotated_reference, reference['layers'])['passed']}
    result = {'schema': 1, 'source_sha256': source_hash, 'limits': LIMITS, 'routes': results,
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'comparison': comparisons, 'negative_controls': negatives, 'production_qualified': False,
              'brightness_comparison': brightness,
              'brightness_accepted': all(row['passed'] for row in brightness.values()),
              'base_evidence_valid': sparse.get('evidence_valid') is True,
              'direction_and_speed_accepted': all(row['fit_valid'] for row in results.values())
                  and sparse.get('evidence_valid') is True and sparse.get('all_bodies_passed') is True
                  and all(row['passed'] for row in comparisons.values()) and all(negatives.values()),
              'scope': 'Both signed texture phase velocities in source UVs; no full product or brightness acceptance'}
    (output / 'analysis.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'direction_and_speed_accepted': result['direction_and_speed_accepted'],
                      'negative_controls': negatives, 'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('sparse_analysis', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--assets', type=Path, default=ROOT)
    parser.add_argument('--global-search', action='store_true')
    args = parser.parse_args()
    analyze(args.source, args.sparse_analysis, args.output, args.assets, args.global_search)
