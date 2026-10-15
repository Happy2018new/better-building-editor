"""Decode the clone-only native portal stripe control from actual pixels."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter


def decode(image, camera):
    values = np.asarray(image.convert('RGB'))
    masks = []
    for face, points in camera['face_points']:
        if not all(point['isInScreen'] for point in points):
            continue
        mask = Image.new('L', image.size)
        ImageDraw.Draw(mask).polygon([(point['screenX'], point['screenY']) for point in points], fill=255)
        interior = np.asarray(mask.filter(ImageFilter.MinFilter(11))) != 0
        masks.append((int(interior.sum()), face, interior))
    if not masks or max(row[0] for row in masks) < 100:
        return {'control_observed': False, 'reason': 'No resolved native face'}
    count, face, interior = max(masks, key=lambda row: row[0])
    stripes = np.broadcast_to((np.arange(values.shape[1]) // 4) % 32, values.shape[:2])
    rows = []
    valid_pixels = 0
    for depth in range(32):
        selected = interior & (stripes == depth)
        region = values[selected].astype(float)
        if len(region) < 100:
            rows.append({'layer': depth, 'sample_pixels': len(region), 'resolved': False})
            continue
        expected_blue = (0.25 + 0.75 * depth / 32.) * 255.
        colored = ((region[:, :2].min(axis=1) >= 62) &
                   (abs(region[:, 2] - expected_blue) <= 3.))
        coverage = float(colored.mean())
        if coverage > .95:
            samples = region[colored]
            median = np.median(samples, axis=0)
            spread = float(np.max(np.percentile(abs(samples - median), 99, axis=0)))
            present = spread <= 2.
            row = {'layer': depth, 'sample_pixels': len(region), 'resolved': True,
                   'present': present, 'coverage': coverage, 'rgb_median': median.tolist(),
                   'rgb_p99_spread': spread,
                   'color_uv': ((median[:2] / 255. - .25) / .75).tolist(),
                   'encoded_depth': float((median[2] / 255. - .25) / .75 * 32.)}
            if present:
                valid_pixels += len(region)
        else:
            row = {'layer': depth, 'sample_pixels': len(region), 'resolved': True,
                   'present': False, 'coverage': coverage,
                   'black_coverage': float((region.max(axis=1) <= 2).mean())}
        rows.append(row)
    observed = ([row['layer'] for row in rows if row.get('present')] if
                all(row['resolved'] for row in rows) else [])
    sentinel_ratio = valid_pixels / float(count)
    valid = len(observed) >= 4 and sentinel_ratio > .25
    return {'schema': 1, 'control_observed': valid, 'pixel_acceptance': False,
            'face': face, 'interior_pixels': count, 'sentinel_ratio': sentinel_ratio,
            'observed_layers': observed if valid else [], 'layers': rows,
            'limits': ['The diagnostic is accepted only when multiple uniform depth stripes are present.',
                       'This measures native attributes, not projection appearance parity.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--capture', default='end_gateway_native_front')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_bytes())
    row = report['captures'][args.capture]
    source = args.report.parent / Path(row['capture']['path']).name
    with Image.open(source) as image:
        result = decode(image, row['camera'])
    result.update(source_report=str(args.report), capture=args.capture,
                  source_report_sha256=hashlib.sha256(args.report.read_bytes()).hexdigest(),
                  capture_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  host_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps({key: result[key] for key in ('control_observed', 'observed_layers', 'pixel_acceptance')}))


if __name__ == '__main__':
    main()
