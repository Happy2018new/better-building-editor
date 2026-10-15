"""Freeze phase-independent water coordinates and independent flat references."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil

import numpy as np
from PIL import Image

from liquid_coordinate_markers import fingerprint, manifest, write

ROOT = Path(__file__).resolve().parents[1]
EPOCHS = ('low', 'high', 'coordinate', 'complement')
LOW, HIGH = 16, 240


def frame(epoch):
    if epoch not in EPOCHS:
        raise ValueError('Unknown immutable static coordinate epoch')
    result = np.empty((32, 32, 4), dtype=np.uint8)
    x, y = np.meshgrid(np.arange(32), np.arange(32))
    if epoch in ('low', 'high'):
        result[:, :, :3] = LOW if epoch == 'low' else HIGH
    else:
        result[:, :, 0] = np.rint(LOW + (HIGH - LOW) * y / 31)
        result[:, :, 1] = np.rint(LOW + (HIGH - LOW) * ((3*x + 5*y) % 32) / 31)
        result[:, :, 2] = np.rint(LOW + (HIGH - LOW) * x / 31)
        if epoch == 'complement':
            result[:, :, :3] = LOW + HIGH - result[:, :, :3].astype(np.int16)
    result[:, :, 3] = 255
    return result


def verify_strip(path, epoch):
    with Image.open(path) as image:
        pixels = np.asarray(image.convert('RGBA'))
    expected = np.tile(frame(epoch), (32, 1, 1))
    if pixels.shape != (1024, 32, 4) or not np.array_equal(pixels, expected):
        raise ValueError('All native frame slots must contain the exact immutable epoch')
    return {'dimensions': [32, 1024], 'identical_square_frames': 32, 'opaque_alpha': True}


def prepare(base, old_plan):
    if base.exists():
        raise ValueError('Choose a fresh static coordinate evidence root')
    original = json.loads(old_plan.read_bytes())
    # Geometry and control values are frozen inputs; failed photometric scores are not reused.
    geometry_refs = [original['geometry_contract'], original['geometry_analysis']]
    geometry_refs += original['geometry_analysis_sources']
    for row in geometry_refs:
        if fingerprint(row['path'])['sha256'] != row['sha256']:
            raise ValueError('Independent geometry source changed')
    assets = {}
    for epoch in EPOCHS:
        path = base / 'assets' / epoch / 'water_flow_grey.png'
        path.parent.mkdir(parents=True)
        Image.fromarray(np.tile(frame(epoch), (32, 1, 1))).save(path)
        assets[epoch] = dict(fingerprint(path), **verify_strip(path, epoch))
    sources = {}
    for name in ('tools/liquid_static_coordinate_epochs.py', 'tools/capture_liquid_static_coordinates.py',
                 'tools/analyze_liquid_static_coordinates.py', 'tools/liquid_coordinate_markers.py',
                 'tools/analyze_liquid_coordinate_markers.py', 'tools/measure_native_liquid_side_uv.py',
                 'tools/diagnose_liquid_coordinate_sampling.py', 'tools/analyze_liquid_workspace.py',
                 'tools/camera_projection.py', 'tools/capture_native_window.py',
                 'tools/verify_camera_projection.py', 'tools/capture_frozen_liquid_controls.py',
                 'tools/capture_pure_liquid_native_controls.py', 'tools/verify_dripstone_direct_seed.py',
                 'tools/verify_wet_actor_visuals.py', 'tools/verify_sign_visuals.py',
                 '.runtime/capture_static_water_controls_r9.py', '.runtime/calibrate_close_water_camera_r9.py',
                 '.runtime/static_coordinate_session_r11.py'):
        live = ROOT / name
        archive = base / 'sources' / name
        archive.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(live, archive)
        sources[name] = {'live': fingerprint(live), 'archive': fingerprint(archive)}
    live = ROOT.parents[1]/'tools/capture_frozen_liquid_controls.py'
    archive = base/'sources/reviewed_frozen_harness.py'
    shutil.copyfile(live, archive)
    sources['reviewed_frozen_harness.py'] = {'live': fingerprint(live), 'archive': fingerprint(archive)}
    target = ROOT / 'resource_pack/textures/blocks/water_flow_grey.png'
    if target.exists():
        raise ValueError('Static experiment requires originally absent flow override')
    plan = {key: original[key] for key in ('geometry_contract', 'geometry_analysis',
                'geometry_analysis_sources', 'geometry_sequences', 'geometry_roles', 'origin',
                'camera_offset', 'controls', 'sample_control', 'sample_grid', 'hypotheses')}
    plan.update(schema=1, created_at=datetime.now(timezone.utc).isoformat(), project=str(ROOT),
        old_geometry_plan=fingerprint(old_plan), frozen_sources=sources, assets=assets,
        epochs=list(EPOCHS), target=str(target), baseline_resource_manifest=manifest(ROOT),
        static_phase_contract='All 32 square frames byte-identical in every epoch; no time or candidate labels',
        photometry='Per-native-pixel low/high reference normalization, fixed before candidate scoring; complement and dry controls test stability',
        limits={'maximum_rgb_rmse': 3., 'minimum_explained_variance': .9,
                'minimum_texture_rms': 2., 'minimum_property_margin_rmse': .5,
                'minimum_green_blue_reference_spread': 40., 'minimum_red_reference_spread': 8., 'maximum_dry_control_rmse': 3.,
                'maximum_complement_source_rmse': 3.},
        installed_native_sources=[fingerprint(Path('D:/MCStudioDownload/game/MinecraftPE_Netease/3.9.0.401155/data')/name)
            for name in ('shaders/glsl/util.h', 'shaders/glsl/renderchunk.fragment',
                         'resource_packs/vanilla/blocks.json', 'resource_packs/vanilla/textures/terrain_texture.json',
                         'resource_packs/vanilla/textures/flipbook_textures.json')],
        configuration=fingerprint(ROOT/'.mcdev.json'), original_configuration_absent=True,
        sampler_boundary='Base-level conventional texture; native TexelAA is a conditional installed-source port. Actual GPU macros, atlas downscale/mips and camera quantization need independent review before production',
        stop_native_and_restore_by_shanghai='2026-10-13T06:20:00+08:00',
        native_uv_accepted=False, production_accepted=False)
    write(base / 'plan.json', plan)
    return fingerprint(base / 'plan.json')


def check(plan):
    for name, rows in plan['frozen_sources'].items():
        if fingerprint(rows['live']['path']) != rows['live'] or fingerprint(rows['archive']['path']) != rows['archive']:
            raise ValueError('Frozen static experiment source changed: ' + name)
    for epoch, asset in plan['assets'].items():
        if fingerprint(asset['path'])['sha256'] != asset['sha256']:
            raise ValueError('Static coordinate bitmap changed')
        verify_strip(asset['path'], epoch)
    for source in plan['installed_native_sources']+[plan['configuration']]:
        if fingerprint(source['path']) != source:
            raise ValueError('Frozen installed native source or configuration changed')


def install(plan, epoch, receipt):
    check(plan)
    if epoch not in EPOCHS or manifest(ROOT) != plan['baseline_resource_manifest']:
        raise ValueError('Resource baseline differs before immutable epoch installation')
    target = Path(plan['target'])
    if target.exists():
        raise ValueError('Original flow-override absence was not restored')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(plan['assets'][epoch]['path'], target)
    write(receipt, {'epoch': epoch, 'target': fingerprint(target),
                    'baseline_originally_absent': True, 'all_frames_identical': verify_strip(target, epoch)})


def restore(plan, epoch, receipt):
    target = Path(plan['target'])
    if not target.is_file() or fingerprint(target)['sha256'] != plan['assets'][epoch]['sha256']:
        raise ValueError('Refusing to remove an unknown resource override')
    target.unlink()
    same = manifest(ROOT) == plan['baseline_resource_manifest']
    write(receipt, {'epoch': epoch, 'original_absence_restored': not target.exists(),
                    'full_resource_manifest_equals_baseline': same})
    if not same:
        raise ValueError('Resource manifest was not restored')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('prepare', 'install', 'restore'))
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--geometry-plan', type=Path)
    parser.add_argument('--epoch', choices=EPOCHS)
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    if args.step == 'prepare':
        if args.geometry_plan is None:
            parser.error('Prepare requires the independent original geometry plan')
        print(json.dumps(prepare(args.base.resolve(), args.geometry_plan.resolve())))
    else:
        if args.epoch is None or args.receipt is None:
            parser.error('Install/restore require an explicit epoch and fresh receipt')
        plan = json.loads((args.base / 'plan.json').read_bytes())
        (install if args.step == 'install' else restore)(plan, args.epoch, args.receipt)


if __name__ == '__main__':
    main()
