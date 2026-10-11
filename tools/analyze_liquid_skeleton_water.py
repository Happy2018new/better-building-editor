"""Replay native water movement, frozen, tint and single-face alpha controls."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageFilter


def rgb(path):
    with Image.open(path) as image:
        return image.convert('RGB')


def maximum(image):
    red, green, blue = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def mask(image, baseline, roi):
    signal = maximum(ImageChops.difference(image, baseline)).point(lambda value: 255 if value > 6 else 0)
    bounds = Image.new('L', image.size)
    bounds.paste(255, roi)
    return ImageChops.multiply(signal, bounds).filter(ImageFilter.MinFilter(3))


def changes(first, second, region):
    delta = maximum(ImageChops.difference(first, second))
    values = np.asarray(delta)[np.asarray(region) > 0]
    return {'pixels_gt2': int(np.count_nonzero(values > 2)),
            'pixels': int(values.size), 'maximum_delta': int(values.max()) if values.size else 0}


def residual(actual, expected, region):
    delta = np.max(np.abs(actual.astype(float) - expected), axis=2)
    values = delta[np.asarray(region) > 0]
    return {'pixels': int(values.size), 'maximum_error': float(values.max()) if values.size else None,
            'pixels_error_le2': int(np.count_nonzero(values <= 2)),
            'passed': bool(values.size >= 1000 and np.all(values <= 2))}


def analyze(path):
    report = json.loads(path.read_bytes())
    captures = report['captures']
    images = {label: rgb(row['path']) for label, row in captures.items()}
    first = images['animated_0']
    width, height = first.size
    rois = [(0, int(height * .12), width // 2, int(height * .95)),
            (width // 2, int(height * .12), width, int(height * .95))]
    masks = [mask(first, images['empty'], roi) for roi in rois]
    mask_rows = []
    for region, roi in zip(masks, rois):
        bounds = region.getbbox()
        mask_rows.append({'bounds': bounds, 'pixels': region.histogram()[255],
                          'framed': bool(bounds and bounds[0] > roi[0] + 2 and bounds[1] > roi[1] + 2
                                         and bounds[2] < roi[2] - 2 and bounds[3] < roi[3] - 2)})
    temporal = []
    for index in range(1, 6):
        temporal.append({'frame': index, 'animated': changes(first, images['animated_' + str(index)], masks[0]),
                         'frozen': changes(first, images['animated_' + str(index)], masks[1])})
    negative = [changes(images['empty'], images['hidden'], region) for region in masks]
    frozen_top = mask(images['top'], images['empty'], rois[1])
    background = np.asarray(images['empty']).astype(float)
    top = np.asarray(images['top']).astype(float)
    half = residual(np.asarray(images['top_half']), (top + background) / 2., frozen_top)
    opacity = report['contract']['textures']['still_water_grey']['alpha_range'][0] / 255.
    top_color = np.array(report['observations']['top_only'][1]['color'], dtype=float)
    swamp_color = np.array(report['observations']['top_swamp'][1]['color'], dtype=float)
    swamp_opacity = report['observations']['top_swamp'][1]['native_opacity']
    texel = (top - background * (1. - opacity)) / opacity / top_color
    expected_swamp = texel * swamp_color * swamp_opacity + background * (1. - swamp_opacity)
    swamp = residual(np.asarray(images['top_swamp']), expected_swamp, frozen_top)
    capture_identity = tuple(captures['animated_0'][key] for key in ('owner', 'game_pid', 'game_identity'))
    verified = all(all(row.get(key) for key in ('ok', 'reliable', 'background_only', 'background_safe'))
                   and tuple(row[key] for key in ('owner', 'game_pid', 'game_identity')) == capture_identity
                   and row['frame']['frame_qpc_100ns'] >= row['frame']['request_qpc_100ns']
                   and hashlib.sha256(Path(row['path']).read_bytes()).hexdigest() == row['sha256']
                   for row in captures.values())
    ready_rows = [row for key, row in report['observations'].items() if key.endswith('_ready') and 'active_ids' in row]
    independent = all(len(row['active_ids']) == 2 and len(set(row['active_ids'])) == 2 for row in ready_rows
                      if row['active_ids'])
    moving = bool(all(row['animated']['pixels_gt2'] >= 1000 for row in temporal))
    frozen = bool(all(row['frozen']['pixels_gt2'] == 0 for row in temporal))
    hidden = bool(all(row['pixels_gt2'] == 0 for row in negative))
    motion = report['observations'].get('motion_ready', {}).get('rows', [])
    stable_pose_id = bool(len(motion) == 16 and len({row['before'] for row in motion}) == 1
                          and all(row['before'] == row['after'] and row['submitted'] and row['payload_ready'] for row in motion))
    acceptance = bool(report['completed'] and report['restored'] and verified and independent
                      and all(row['framed'] and row['pixels'] >= 1000 for row in mask_rows))
    return {'schema': 1, 'input': str(path.resolve()), 'input_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'control_rois': rois, 'masks': mask_rows, 'captures_verified': verified, 'independent_ids': independent,
            'temporal': temporal, 'animated_pixels_change': moving, 'frozen_pixels_stable': frozen,
            'hidden_pixels': negative, 'hidden_control_matches_background': hidden,
            'single_face_projection_alpha': half, 'single_face_explicit_opacity': swamp,
            'continuous_pose_id_stable': stable_pose_id,
            'pose_signal': [changes(images['restored_plains'], images['motion_end'], region) for region in masks],
            'native_artwork_animation_observed': acceptance and moving and frozen and hidden,
            'candidate_alpha_contract_observed': acceptance and half['passed'] and swamp['passed'],
            'native_shape_accepted': False, 'native_uv_accepted': False, 'native_alpha_accepted': False,
            'production_editor_accepted': False, 'production_world_accepted': False, 'production_memory_accepted': False,
            'scope': 'Original-artwork temporal control and candidate alpha contract, not native liquid tessellator acceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a fresh analysis report')
    report = analyze(args.input)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report))
    return 0 if report['native_artwork_animation_observed'] and report['candidate_alpha_contract_observed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
