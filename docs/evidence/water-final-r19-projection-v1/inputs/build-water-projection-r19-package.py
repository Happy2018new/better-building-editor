"""Archive the rejected v5 pixel batch and numerical projection diagnosis."""
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / '.runtime/water-final-r19-world-v5'
OLD = ROOT / '.runtime/water-final-r19-world-v4'
DEST = ROOT / 'docs/evidence/water-final-r19-projection-v1'
if DEST.exists():
    raise ValueError('Choose a fresh package')
DEST.mkdir()
(DEST / 'v5').mkdir()
(DEST / 'v4').mkdir()
(DEST / 'inputs').mkdir()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(name, value):
    (DEST / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='ascii')


for path in RAW.iterdir():
    if path.is_file():
        shutil.copyfile(path, DEST / 'v5' / path.name)
for name in ('world.json', 'calibration.json', 'world_full_pool_wet_side_opaque.png',
             'world_full_pool_wet_side_opaque.capture.json'):
    shutil.copyfile(OLD / name, DEST / 'v4' / name)
for name in ('water-native-projection-r19.py', 'run-water-final-r19.py',
             'build-water-projection-r19-package.py'):
    shutil.copyfile(ROOT / '.runtime' / name, DEST / 'inputs' / name)
shutil.copyfile(ROOT / '.runtime/water-final-r19-v1/launch-inputs.zip', DEST / 'launch-inputs.zip')

summary = {
    'schema': 1, 'production_qualified': False, 'product_admission_performed': False,
    'shader_or_resource_changes': False, 'original_acceptance_overwritten': False,
    'current_source_contract': '20ab6570d676d884753b89ca2d6f35508e17e7dfac47909c245e26e86a5cf272',
    'v5_session': {'id': 'ed4c642a9db84fee92cf0c0cda5d2630', 'game_pid': 50076, 'mcdk_pid': 9536,
                   'owner': 'water-final-r19', 'stopped_normally': True, 'owned_pids_absent': True,
                   'force_used': False},
    'v5_water_pixels_valid': False,
    'v5_rejection': 'All six world PNGs have one identical SHA and retain the previous stone calibration viewport; fresh WGC timestamps did not imply fresh rendered content.',
    'v5_completed_restored_source_unchanged': True, 'v5_cleanup_errors': [],
    'v5_actual_uniform_vectors': 256, 'v5_uniform_float32_mismatches': 0,
    'physical_native_projection_units_confirmed_on_stone': True,
    'numerical_native_camera_intrinsics': {'center': [997.4998, 553.5], 'focal_pixels': 852.3152,
        'api_numeric_fit_max_residual_pixels': .00006, 'fit_uses_images': False},
    'native_stone_api_hull_iou': {'front': .9745201989068344, 'right': .9745201989068344,
                                'tilted': .9692268348819367},
    'cross_session_diagnostic': {
        'acceptance': False, 'same_declared_pose_viewport_origin_source': True,
        'original_grid': {'south': {'correlation': .9492226198204802, 'rgb_rmse': 2.9280922504339943},
                          'east': {'correlation': .93705014290488, 'rgb_rmse': 3.1498727726276847}},
        'fixed_texel_centers': {'south_correlation': 1., 'east_correlation': 1., 'rgb_rmse': 0.},
        'all_four_artwork_luminance_correlation': .9999006289239981,
        'all_mirror_constant_wrong_phase_negatives_rejected': True,
        'limitation': 'v5 numerical API points are replayed over v4 valid water pixels. v5 itself has no valid water pixels.'},
    'finding': 'The localized apparent one-texel anomaly is explained by the analytical projection oracle under the cross-session numerical mapping. No water shader correction is justified by these data.',
    'remaining': 'A fresh same-session water image pair with native points, independent stone checks, and nonzero wet/dry/section geometry contributions is still required for acceptance.'}
save('summary.json', summary)

contact = Image.new('RGB', (1200, 410), 'white')
draw = ImageDraw.Draw(contact)
for index, (name, path) in enumerate((('v4 VALID water; original oracle UV failures preserved',
    DEST / 'v4/world_full_pool_wet_side_opaque.png'), ('v5 INVALID world capture; previous stone viewport',
    DEST / 'v5/world_full_pool_wet_side_opaque.png'))):
    image = Image.open(path).convert('RGB')
    image.thumbnail((590, 365))
    contact.paste(image, (index * 600 + 5, 36))
    draw.text((index * 600 + 5, 8), name, fill='black')
contact.save(DEST / 'contact-valid-v4-invalid-v5.png')

(DEST / 'README.md').write_text('''# Water r19 projection-oracle diagnostic

The apparent one-texel error in east cell `(4,3,3)` is strongly explained by the
analytical projection used by the sampling oracle. No shader, UV formula,
texture, product gate, or acceptance threshold was changed. This package is
diagnostic evidence and does not qualify production water.

The original valid v4 captures and failed original `18 x 14` checks remain in
`../water-final-r19-world-v1/`. This package retains the exact v4 opaque frame
used by the offline cross-check. The declared physical side formulas agree
with the frozen shader: east `(x+1,y+h,z+u)`, south `(x+1-u,y+h,z+1)` and texture
pixel centers `u*15+0.5`, `(1-h)*15+0.5`.

`v5/plan.json` and its receipt were written before the short v5 session. That
plan fixes the original physical grid, texel-center grid, pixel-center
conventions, and mirrored/constant/wrong-phase/wrong-UI-scaling negatives.
`v5/calibration-native.json` records public `WorldToScreenPoint` outputs on
three independent stone views. Its coordinates are physical pixels. A
numerical fit of those API values alone gives center `(997.4998,553.5000)` and
focal length `852.3152 px`, with residual below `0.00006 px`. This fit is a
diagnostic, never acceptance. The native API hull itself differs from the
stone raster by about two vertical pixels and has IoU `0.9692-0.9745`; it must
not be described as exact pixel truth.

The v5 world batch completed and restored without source changes, but all six
world screenshots are **invalid**: their SHA-256 values are identical and the
viewport still shows the preceding stone calibration. Each WGC receipt has a
fresh compositor timestamp. That timing does not prove fresh game rendering.
`v5/invalid-stale-capture-audit.json` retains the rejection, and the contact
image makes the error visible. Apparent texture correlations in
`v5/native-projection-analysis.json` were generated before visual inspection
and are rejected along with the v5 pixels. Sky gradients produced those
misleading correlations. Any subsequent verifier must require independent
nonzero wet/dry and section-hidden contributions before assessing UV.

The v5 numerical camera and native uniform observations are retained
separately. All 256 native uniform vectors match their expected float32
values. The public native projection differs from the old analytical oracle
by up to about 4.46 physical pixels over the declared water samples. Replaying
the fixed native coordinates over the old **valid v4 water frame**, under the
identical declared camera/viewport/document origin, gives original-grid south
correlation `0.94922`, RMSE `2.92809`, and east correlation `0.93705`, RMSE
`3.14987`; all erroneous controls reject. Both fixed texel-center side pairs
are exactly equal, RGB RMSE `0`, and all four cells match the frozen artwork
with luminance correlation `0.99990063`. These are cross-session diagnostics;
they do not replace the failed original v4 acceptance result.

The appropriate next step is a fresh same-session capture with public native
points, independent stone controls, verified changing water pixels, and the
unchanged grid and thresholds. The evidence does not support adding a
cell-specific UV offset or changing the water shader.

Run `python -X utf8 verify_package.py --pixels` to verify hashes, frozen
source inputs, rejected stale frames, native uniforms, and offline pixel
diagnostics. No game or desktop interaction is performed by the verifier.
''', encoding='utf8')

VERIFIER = r'''"""Verify rejected capture evidence and replay the projection diagnostic."""
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
'''
(DEST / 'verify_package.py').write_text(VERIFIER, encoding='utf8')
files = {path.relative_to(DEST).as_posix(): {'bytes': path.stat().st_size, 'sha256': sha(path)}
         for path in sorted(DEST.rglob('*')) if path.is_file()}
save('manifest.json', {'schema': 1, 'files': files, 'production_qualified': False})
print(json.dumps({'package': str(DEST), 'manifest_files': len(files),
                  'bytes': sum(row['bytes'] for row in files.values()), 'production_qualified': False}))
