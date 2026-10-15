"""Verify rejected capture evidence and replay the projection diagnostic."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name):
    return json.loads((ROOT / name).read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pixels', action='store_true')
    args = parser.parse_args()
    for name, row in read('manifest.json')['files'].items():
        path = ROOT / name
        assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256'], name
    summary = read('summary.json')
    assert summary['production_qualified'] is False and summary['v5_water_pixels_valid'] is False
    plan = read('v5/plan.json')
    assert sha(ROOT / 'v5/plan.json') == read('v5/plan-receipt.json')['sha256']
    assert plan['tool_sha256'] == sha(ROOT / 'inputs/water-native-projection-r19.py')
    launch = read('v5/launch-inputs.json')
    source, previous = read('v5/world.json'), read('v4/world.json')
    assert source['source_contract_sha256'] == previous['source_contract_sha256'] == plan['frozen_source_contract']
    assert source['source_unchanged'] and source['restored'] and source['completed'] and not source['cleanup_errors']
    assert len(source['captures']) == 6
    assert len({row['sha256'] for row in source['captures'].values()}) == 1
    calibration = read('v5/calibration.json')
    frames = list(source['captures'].values())
    frames += [frame for row in calibration['views'] for frame in (row['shown'], row['hidden'])]
    for row in frames:
        path = ROOT / 'v5' / Path(row['path']).name
        assert sha(path) == row['sha256']
        receipt = json.loads(path.with_suffix('.capture.json').read_bytes())
        assert receipt['reliable'] and receipt['guarded_no_activation']
        assert receipt['agent_activation_allowed'] is False and receipt['activation_fallback'] is False
        assert receipt['game_pid'] == source['session_binding']['game_pid']
        assert receipt['frame']['frame_qpc_100ns'] >= receipt['frame']['request_qpc_100ns']
    native = read('v5/world-native.json')
    import numpy as np
    vectors = 0
    for frames in native.values():
        for row in frames.values():
            for group in row['groups']:
                for index, expected in enumerate(group['group'][3], 1):
                    assert group['actual_uniforms'][str(index)] == np.asarray(expected, dtype=np.float32).astype(float).tolist()
                    vectors += 1
    assert vectors == 256
    with zipfile.ZipFile(ROOT / 'launch-inputs.zip') as archive:
        assert set(archive.namelist()) == set(launch['source_sha256'])
        for name, expected in launch['source_sha256'].items():
            assert hashlib.sha256(archive.read(name)).hexdigest() == expected
        if args.pixels:
            with tempfile.TemporaryDirectory(prefix='water-r19-projection-replay-') as folder:
                temporary = Path(folder)
                for name in archive.namelist():
                    if name.startswith(('tools/', 'behavior_pack/')) and name.endswith('.py'):
                        archive.extract(name, temporary)
                sys.path.insert(0, str(temporary / 'tools'))
                from analyze_product_water import rgb
                from analyze_water_acceptance_r16 import repetition
                from scipy.ndimage import map_coordinates
                image = rgb(ROOT / 'v4/world_full_pool_wet_side_opaque.png')
                assert sha(ROOT / 'v4/world_full_pool_wet_side_opaque.png') == previous['captures']['full_pool_wet_side_opaque']['sha256']
                stale = rgb(ROOT / 'v5/world_full_pool_wet_side_opaque.png')
                last_stone = rgb(ROOT / 'v5/calibration_tilted_shown.png')
                assert not np.any(np.max(abs(stale[120:].astype(int) - last_stone[120:].astype(int)), axis=2) > 8)
                readings = native['world_full_pool_wet_side_opaque']
                observed = {}
                for name, grid in plan['grids'].items():
                    points = readings['before']['projection'][name]
                    assert points == readings['after']['projection'][name]
                    xy = np.asarray([(point['screenX'], point['screenY']) for point in points])
                    samples = np.stack([map_coordinates(image[:, :, channel].astype(float),
                        (xy[:, 1] - .5, xy[:, 0] - .5), order=1, mode='nearest') for channel in range(3)], axis=1)
                    observed[name] = samples.reshape(tuple(grid['dimensions']) + (3,))
                archived = read('v5/prior-v4-transferred-native-diagnostic.json')['variants']['0.5']
                for grid in ('original', 'texel_centers'):
                    for face, cells in (('south', ('3_3_4', '4_3_4')), ('east', ('4_3_3', '4_3_4'))):
                        first, second = [observed[grid + '_' + face + '_' + cell] for cell in cells]
                        actual = repetition(first, second)
                        expected = archived[grid + '_' + face]
                        for key in ('passed', 'correlation', 'contrast', 'rgb_rmse'):
                            assert actual[key] == expected[key], (grid, face, key)
                        assert actual['passed']
                        for wrong in (second[:, ::-1], np.full_like(second, second.mean()), np.roll(second, 5, axis=1)):
                            assert not repetition(first, wrong)['passed']
                        if grid == 'texel_centers':
                            assert np.array_equal(first, second) and actual['rgb_rmse'] == 0.
                from PIL import Image
                import io
                texture = np.array(Image.open(io.BytesIO(archive.read('resource_pack/textures/models/modern_projection/liquid/flowing_water_grey.png'))).convert('RGB'))
                artwork = texture[5:13, 2:14].mean(axis=2).ravel()
                for key, sample in observed.items():
                    if key.startswith('texel_centers'):
                        assert abs(float(np.corrcoef(artwork, sample.mean(axis=2).ravel())[0, 1]) - .9999006289239981) < 1e-12
    print(json.dumps({'verified': True, 'v5_water_pixels_rejected': 6, 'native_uniform_vectors': vectors,
                      'cross_session_diagnostic_replayed': args.pixels, 'production_qualified': False}))


if __name__ == '__main__':
    main()
