"""Measure translation sensitivity without changing native visual acceptance."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageStat
from verify_missing_neighbor_visuals import binary, count, feature_overlap, maximum


def translate(source, x, y):
    result = Image.new(source.mode, source.size)
    result.paste(source, (x, y))
    return result


def fit(baseline, actual, threshold=16, max_x=6, max_y=3):
    target = binary(maximum(baseline), threshold)
    rows = []
    for x in range(-max_x, max_x + 1):
        for y in range(-max_y, max_y + 1):
            moved = translate(actual, x, y)
            presence = binary(maximum(moved), threshold)
            shared = ImageChops.multiply(target, presence)
            shape = feature_overlap(target, presence)
            color = (ImageStat.Stat(ImageChops.difference(baseline, moved), mask=shared).mean
                     if count(shared) else [255.] * 3)
            rows.append(dict(offset_pixels=(x, y), shape=shape, color_error=color,
                             touches_search_boundary=abs(x) == max_x or abs(y) == max_y))
    return sorted(rows, key=lambda row: (-row['shape']['iou'], max(row['color_error'])))[:8]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--max-x', type=int, default=6)
    parser.add_argument('--max-y', type=int, default=3)
    args = parser.parse_args()
    if not 0 < args.max_x <= 64 or not 0 < args.max_y <= 64:
        parser.error('Search radii must be between 1 and 64 pixels')
    source = json.loads(args.source.read_text(encoding='utf8'))
    report = {'schema': 1, 'source': str(args.source.resolve()),
              'source_sha256': hashlib.sha256(args.source.read_bytes()).hexdigest(),
              'scope': 'Diagnostic sensitivity only; original pass/fail and thresholds remain unchanged',
              'search_radii_pixels': (args.max_x, args.max_y),
              'cases': []}
    for case in source['cases']:
        for view, row in case['dynamic']['views'].items():
            paths = row['pixels']['artifacts']
            first, second = (Path(paths[key]) for key in ('baseline_remaining', 'actual_remaining'))
            with Image.open(first).convert('RGB') as baseline, Image.open(second).convert('RGB') as actual:
                report['cases'].append({'case': case['case'], 'view': view,
                                        'best_translations': fit(baseline, actual, max_x=args.max_x, max_y=args.max_y),
                                        'original_passed': row['pixels']['passed']})
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
