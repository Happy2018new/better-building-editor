"""Infer native clock direction from isolated RGB frames, independent of fluid UVs."""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


def direction(samples):
    if len(samples) < 8:
        return {'passed': False, 'reason': 'insufficient_frames'}
    intervals = [(right['qpc'] - left['qpc']) / 1e7
                 for left, right in zip(samples, samples[1:])]
    if any(not 0 < value <= .15 for value in intervals):
        return {'passed': False, 'reason': 'invalid_or_aliased_frame_times'}
    delta = [((right['red'] - left['red'] + 128) % 256) - 128
             for left, right in zip(samples, samples[1:])]
    seconds = (samples[-1]['qpc'] - samples[0]['qpc']) / 1e7
    support = [row['support_pixels'] for row in samples]
    increasing = sum(value > 0 for value in delta)
    decreasing = sum(value < 0 for value in delta)
    sign = 1 if increasing and not decreasing else -1 if decreasing and not increasing else 0
    rate = sum(delta) / seconds if seconds > 0 else 0.
    return {'passed': (sign != 0 and increasing + decreasing >= 4
                       and min(support) >= 500 and max(support) <= min(support) * 1.02
                       and 20. <= abs(rate) <= 50.),
            'clock_direction': sign, 'red_differences': delta, 'red_per_second': rate,
            'changed_pairs': increasing + decreasing, 'support_pixels_range': [min(support), max(support)]}


def analyze_capture(capture):
    from analyze_product_water_flow import burst_frames, sha
    images, times = burst_frames(capture)
    samples = []
    for path, time in zip(images, times):
        with Image.open(path) as image:
            rgb = np.asarray(image.convert('RGB'))
        selected = (rgb[:, :, 1] >= 62) & (rgb[:, :, 1] <= 66) & (rgb[:, :, 2] >= 253)
        counts = np.bincount(rgb[:, :, 0][selected], minlength=256)
        red = int(np.argmax(counts))
        samples.append({'red': red, 'qpc': time, 'support_pixels': int(counts[red]),
                        'png_sha256': sha(path)})
    return dict(direction(samples), samples=samples, helper_sha256=capture['expected_helper_sha256'],
                capture_temporal_complete=capture['temporal_complete'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('capture', type=Path, help='Validated burst wrapper receipt')
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh clock evidence')
    report = dict(analyze_capture(json.loads(args.capture.read_bytes())), schema_version=1,
                  product_acceptance_claimed=False)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: report[key] for key in ('passed', 'clock_direction', 'red_per_second')}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
