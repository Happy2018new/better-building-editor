"""Decode clone-only native/candidate normal and parallax-texel controls.

The shader alternates four-pixel normal/UV rows and selects a plane in
four-pixel columns. TIME changes only UV.y, so UV.x can be compared directly.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode(path, camera, face='north'):
    with Image.open(path) as image:
        values = np.asarray(image.convert('RGB'))
        mask = Image.new('L', image.size)
    points = dict(camera['face_points'])[face]
    if not all(point['isInScreen'] for point in points):
        raise ValueError('The decoded face must be fully visible')
    ImageDraw.Draw(mask).polygon([(p['screenX'], p['screenY']) for p in points], fill=255)
    interior = np.asarray(mask.filter(ImageFilter.MinFilter(11))) != 0
    height, width = interior.shape
    y, x = np.indices((height, width))
    stripes = (x//4) % 32
    normal_band = (((height-1-y)//4) % 2) == 0
    rows, samples = [], {}
    for depth in range(0, 32, 2):
        normal_mask = interior & (stripes == depth) & normal_band
        uv_mask = interior & (stripes == depth) & ~normal_band
        normal, uv = values[normal_mask], values[uv_mask]
        if len(normal) < 50 or len(uv) < 50:
            raise ValueError('The face does not resolve every selected plane')
        median = np.median(normal, axis=0)
        spread = np.max(np.percentile(np.abs(normal.astype(float)-median), 99))
        row = {'depth': depth, 'normal_sample_pixels': len(normal),
               'uv_sample_pixels': len(uv), 'normal_bytes': median.tolist(),
               'normal_decoded': (median/255.*2.-1.).tolist(),
               'normal_rgb_p99_spread': float(spread),
               'depth_byte': float(np.median(uv[:, 2]))}
        rows.append(row)
        samples[depth] = (uv_mask, values)
    expected_depths = [int(index*255./16.) for index in range(16)]
    control = (all(row['normal_rgb_p99_spread'] <= 1. for row in rows) and
               all(max(abs(v) for v in row['normal_decoded']) > .95 for row in rows) and
               [row['depth_byte'] for row in rows] == expected_depths)
    return {'control_observed': control, 'face': face, 'layers': rows}, samples


def compare(first, second):
    rows = []
    for depth in sorted(set(first) & set(second)):
        mask_a, values_a = first[depth]
        mask_b, values_b = second[depth]
        common = mask_a & mask_b
        a, b = values_a[common].astype(int), values_b[common].astype(int)
        delta = (b[:, :2]-a[:, :2]+128) % 256-128
        unique, counts = np.unique(delta[:, 1], return_counts=True)
        phase = int(unique[np.argmax(counts)])
        residual = (delta[:, 1]-phase+128) % 256-128
        rows.append({'depth': depth, 'sample_pixels': len(a),
                     'texel_x_exact_ratio': float(np.mean(delta[:, 0] == 0)),
                     'texel_x_within_one_ratio': float(np.mean(np.abs(delta[:, 0]) <= 1)),
                     'texel_x_abs_error_mean': float(np.mean(np.abs(delta[:, 0]))),
                     'texel_y_fitted_phase': phase,
                     'texel_y_phase_within_one_ratio': float(np.mean(np.abs(residual) <= 1))})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--family', default='end_gateway')
    parser.add_argument('--view', default='front')
    parser.add_argument('--face', default='north')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    result = {'schema': 1, 'pixel_acceptance': False, 'qualification': False,
              'host_sha256': sha(Path(__file__)), 'source_report_sha256': sha(args.report),
              'captures': {}, 'limits': ['Coordinate readback does not establish native appearance.',
                                       'Animation phase is fitted and does not verify speed or direction.']}
    samples = {}
    for kind in ('candidate', 'native'):
        key = args.family+'_'+kind+'_'+args.view
        row = report['captures'][key]
        path = args.report.parent / Path(row['capture']['path']).name
        if sha(path) != row['capture']['sha256']:
            raise ValueError('A bound capture changed')
        decoded, samples[kind] = decode(path, row['camera'], args.face)
        decoded['capture_sha256'] = sha(path)
        result['captures'][kind] = decoded
    result['comparison'] = compare(samples['candidate'], samples['native'])
    result['control_observed'] = all(row['control_observed'] for row in result['captures'].values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'control_observed': result['control_observed'],
                      'normal_bytes': {kind: row['layers'][0]['normal_bytes']
                                       for kind, row in result['captures'].items()},
                      'comparison': result['comparison'], 'qualification': False}))


if __name__ == '__main__':
    main()
