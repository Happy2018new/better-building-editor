"""Rebuild glint samples from lossless pixels and refit both signed phase layers."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image


def retained_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Retained path escapes its package')
    return path


def reconstruct_samples(folder, route, report, catalog, texture):
    from analyze_item_glint_direction_r20 import LIMITS, sample_projection
    provenance = json.loads((folder / (route + '-pixel-sources.json')).read_bytes())
    cached = dict(np.load(folder / (route + '-samples.npz'), allow_pickle=False))
    projection = sample_projection(report, route, texture, catalog['pose'])
    xy = np.asarray(provenance['sample_xy'])
    if not np.array_equal(projection['xy'], xy):
        raise ValueError('Retained pixel coordinates differ from source projection')
    if provenance['source_game_identity'] != report['session']['game_identity']:
        raise ValueError('Retained pixels belong to another game instance')
    burst = report['closeup']['motion_bursts'][route]
    dense_path = folder.parent / 'receipts' / (route + '-dense.json')
    if (not burst['stable'] or hashlib.sha256(dense_path.read_bytes()).hexdigest() != burst['sha256']
            or provenance['dense_receipt_sha256'] != burst['sha256']):
        raise ValueError('Retained dense receipt is not source-bound')
    dense = json.loads(dense_path.read_bytes())
    if (not dense['capture_valid'] or not dense['temporal_complete']
            or dense['instance']['game_identity'] != report['session']['game_identity']):
        raise ValueError('Retained dense receipt is incomplete or belongs to another game')
    frames = [row for row in dense['frames'] if row['png'] is not None]
    if len(frames) != len(provenance['frames']):
        raise ValueError('Retained pixel sources omit source frames')
    for name in ('uv', 'corners'):
        if not np.allclose(cached[name], projection[name], atol=1e-10, rtol=0.):
            raise ValueError('Cached ' + name + ' differs from source projection')
    left, top, right, bottom = provenance['crop_bounds']
    local = xy - (left, top)
    samples, times = [], []
    for index, (row, original) in enumerate(zip(provenance['frames'], frames)):
        receipt_path = folder.parent / 'receipts' / route / ('%04d.json' % (index + 1))
        if (hashlib.sha256(receipt_path.read_bytes()).hexdigest() != original['receipt']['sha256']
                or row['capture_receipt_sha256'] != original['receipt']['sha256']
                or row['full_frame_sha256'] != original['png']['sha256']):
            raise ValueError('Retained frame source hashes differ')
        receipt = json.loads(receipt_path.read_bytes())
        if row['frame_qpc_100ns'] != receipt['frame_qpc_100ns']:
            raise ValueError('Retained timestamp differs from the native receipt')
        path = retained_path(folder, row['retained_crop'])
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['retained_crop_sha256']:
            raise ValueError('Retained crop bytes changed')
        with Image.open(path) as image:
            if image.size != (right - left, bottom - top):
                raise ValueError('Retained crop bounds differ')
            samples.append(np.asarray(image.convert('RGB'))[local[:, 1], local[:, 0]])
        times.append(row['frame_qpc_100ns'] / 1e7)
    times = np.asarray(times) - times[0]
    samples = np.asarray(samples)
    if not np.array_equal(samples, cached['samples']) or not np.array_equal(times, cached['times']):
        raise ValueError('Cached samples or timestamps differ from lossless pixels')
    if (times[-1] < LIMITS['minimum_duration_seconds'] or (np.diff(times) <= 0.).any()
            or np.diff(times).max() > LIMITS['maximum_frame_gap_seconds']):
        raise ValueError('Retained real frame cadence is insufficient')
    return {'uv': projection['uv'], 'corners': projection['corners'],
            'samples': samples, 'times': times}


def verify(package, pixels):
    manifest = json.loads((package / 'manifest.json').read_bytes())
    if manifest['schema'] != 1 or manifest['production_qualified'] is not False:
        raise ValueError('Unexpected glint evidence manifest')
    for relative, expected in manifest['files'].items():
        path = retained_path(package, relative)
        raw = path.read_bytes()
        if len(raw) != expected['bytes'] or hashlib.sha256(raw).hexdigest() != expected['sha256']:
            raise ValueError('Retained bytes changed: ' + relative)
    summary = json.loads((package / 'summary.json').read_bytes())
    results = {}
    if pixels:
        sys.path.insert(0, str(package / 'source/tools'))
        from analyze_item_glint_direction_r20 import (brightness_comparison, direction_comparison,
                                                     fit)
        for label in summary['captures']:
            folder = package / label
            report = json.loads((folder / 'source-report.json').read_bytes())
            expected = json.loads((folder / 'direction/analysis.json').read_bytes())
            catalog = json.loads((folder / 'assets/tools/data/item_icon_catalog_nemc_3.10.0.420447.json').read_bytes())
            resource = next(row['resource'] for row in catalog['items']
                            if (row['name'], row['aux']) == ('minecraft:diamond_sword', 0))
            textures = folder / 'assets/resource_pack/textures/models/modern_projection/item_icons'
            with Image.open(textures / 'enchanted_glint.png') as image:
                glint = np.asarray(image.convert('RGB'))[0, :, 0].astype(float) / 255.
            measured = {}
            with Image.open(textures / (resource + '.png')) as texture:
                for route, previous in expected['routes'].items():
                    samples = reconstruct_samples(folder / 'direction', route, report, catalog, texture)
                    try:
                        actual = fit(samples, glint, expected.get('global_search', True))
                    except ValueError as error:
                        actual = {'fit_valid': False, 'error': str(error), 'layers': []}
                    if actual['fit_valid'] != previous['fit_valid']:
                        raise ValueError('Refit validity differs: ' + label + '/' + route)
                    if previous['fit_valid']:
                        if (not direction_comparison(actual['layers'], previous['layers'])['passed']
                                or abs(actual['nrmse'] - previous['nrmse']) > .0001
                                or not np.allclose(actual['rgb_temporal_gains'],
                                                   previous['rgb_temporal_gains'], rtol=.001, atol=.001)):
                            raise ValueError('Refitted glint measurements differ: ' + label + '/' + route)
                    measured[route] = actual
            reference = measured['native']
            comparison = {route: direction_comparison(row['layers'], reference['layers'])
                          if row['layers'] else {'passed': False, 'status': 'NO_MEASURABLE_GLINT'}
                          for route, row in measured.items() if route != 'native'}
            brightness = {route: brightness_comparison(row, reference)
                          for route, row in measured.items() if route != 'native'}
            if comparison != expected['comparison']:
                for route, row in comparison.items():
                    if row['passed'] != expected['comparison'][route]['passed']:
                        raise ValueError('Replayed direction gate differs')
            if brightness != expected['brightness_comparison']:
                for route, row in brightness.items():
                    if row['passed'] != expected['brightness_comparison'][route]['passed']:
                        raise ValueError('Replayed brightness gate differs')
            results[label] = {'routes_refitted': len(measured),
                              'direction_and_speed_accepted': expected['direction_and_speed_accepted'],
                              'brightness_accepted': expected['brightness_accepted']}
    print(json.dumps({'manifest_files_verified': len(manifest['files']),
                      'pixel_replay': results, 'production_qualified': False}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    verify(args.package.resolve(), args.pixels)
