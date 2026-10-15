"""Review matched shelf candidates; role scores remain diagnostic observations."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def pixels(report, label, directory):
    receipt = report['captures'][label]
    source = Path(receipt['path'])
    if not source.is_file():
        source = directory / source.name
    if receipt.get('reliable') is not True:
        raise ValueError('Unreliable shelf capture: ' + label)
    if hashlib.sha256(source.read_bytes()).hexdigest() != receipt['sha256']:
        raise ValueError('Shelf capture bytes changed: ' + label)
    projection = receipt['before']['target_screen']
    if projection.get('isInScreen') is not True:
        raise ValueError('Shelf target is outside the captured viewport')
    with Image.open(source) as picture:
        # Native WorldToScreenPoint returns physical pixels, not logical UI units.
        center_x, center_y = projection['screenX'], projection['screenY']
        bounds = (round(center_x - 190), round(center_y - 170),
                  round(center_x + 190), round(center_y + 130))
        if min(bounds) < 0 or bounds[2] > picture.width or bounds[3] > picture.height:
            raise ValueError('Shelf review crop extends beyond the viewport')
        return np.asarray(picture.convert('RGB').crop(bounds))


def compare(reference, candidate, empty):
    if reference.shape != candidate.shape or reference.shape != empty.shape:
        raise ValueError('Shelf frames have different dimensions')
    native_mask = np.max(np.abs(reference.astype(float) - empty), axis=2) > 12
    candidate_mask = np.max(np.abs(candidate.astype(float) - empty), axis=2) > 12
    union = native_mask | candidate_mask
    if np.count_nonzero(native_mask) < 100 or np.count_nonzero(candidate_mask) < 100:
        raise ValueError('Missing native or candidate shelf content')
    ys, xs = np.nonzero(native_mask)
    left, top, right, bottom = int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1
    width, height = right - left, bottom - top
    bounds = [left, top, right, bottom]
    common = native_mask & candidate_mask
    # Score the shelf's middle backing; outer rails are shared by all roles.
    middle = np.zeros_like(common)
    middle[top + int(height * .31):top + int(height * .66),
           left + int(width * .08):left + int(width * .92)] = True
    middle &= common
    if np.count_nonzero(middle) < 100:
        raise ValueError('Shelf middle artwork is too small to inspect')
    first = reference[middle].astype(float)
    second = candidate[middle].astype(float)
    gain = np.sum(first * second, axis=0) / np.maximum(np.sum(second * second, axis=0), 1.)
    normalized = second * gain
    correlations = []
    for channel in range(3):
        if min(np.std(first[:, channel]), np.std(second[:, channel])) < 1e-6:
            correlations.append(None)
        else:
            correlations.append(float(np.corrcoef(first[:, channel], second[:, channel])[0, 1]))
    return {'native_pixels': int(native_mask.sum()), 'candidate_pixels': int(candidate_mask.sum()),
            'unshifted_iou': float(np.count_nonzero(common) / np.count_nonzero(union)),
            'native_bounds': bounds, 'middle_pixels': int(middle.sum()),
            'middle_rgb_gain': gain.tolist(), 'middle_channel_correlation': correlations,
            'middle_normalized_rmse': float(np.sqrt(np.mean((first - normalized) ** 2))),
            'middle_raw_rmse': float(np.sqrt(np.mean((first - second) ** 2)))}


def analyze(source, output):
    report = json.loads(source.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Shelf measurement did not complete and restore unchanged sources')
    if report.get('cleanup_errors'):
        raise ValueError('Shelf measurement has cleanup errors')
    output.mkdir(parents=True, exist_ok=False)
    rows = []
    tiles = []
    max_columns = 0
    for case in report['cases']:
        label = case['label']
        native = pixels(report, label + '_world', source.parent)
        empty = pixels(report, label + '_empty', source.parent)
        records = {}
        samples = [('world', native)]
        for key in report['captures']:
            if key.startswith(label + '_') and key not in (label + '_world', label + '_empty'):
                front = key[len(label) + 1:]
                candidate = pixels(report, key, source.parent)
                records[front] = compare(native, candidate, empty)
                samples.append((front, candidate))
        if not records:
            raise ValueError('No candidate artwork for ' + label)
        ranking = sorted(records, key=lambda key: records[key]['middle_normalized_rmse'])
        row = {'label': label, 'states': case['states'], 'scores': records,
               'best_diagnostic_match': ranking[0],
               'diagnostic_rmse_margin': (records[ranking[1]]['middle_normalized_rmse'] -
                                          records[ranking[0]]['middle_normalized_rmse'])
               if len(ranking) > 1 else None}
        rows.append(row)
        left, top, right, bottom = records[ranking[0]]['native_bounds']
        bounds = (max(0, left - 8), max(0, top - 8), min(native.shape[1], right + 8),
                  min(native.shape[0], bottom + 8))
        row['review_bounds'] = list(bounds)
        for front, array in samples:
            crop = Image.fromarray(array).crop(bounds)
            crop.save(output / (label + '_' + front + '.png'))
        tiles.append((label, [(front, Image.fromarray(array).crop(bounds)) for front, array in samples]))
        max_columns = max(max_columns, len(samples))
    tile_width = max(picture.width for unused, samples in tiles for unused, picture in samples)
    tile_height = max(picture.height for unused, samples in tiles for unused, picture in samples) + 42
    sheet = Image.new('RGB', (max_columns * tile_width, len(tiles) * tile_height), '#252525')
    draw = ImageDraw.Draw(sheet)
    for y, (label, samples) in enumerate(tiles):
        for x, (front, picture) in enumerate(samples):
            draw.text((x * tile_width + 3, y * tile_height + 3), label, fill='white')
            draw.text((x * tile_width + 3, y * tile_height + 19), front, fill='white')
            sheet.paste(picture, (x * tile_width, y * tile_height + 40))
    sheet.save(output / 'review.png')
    result = {'schema_version': 1, 'production_qualified': False,
              'source_report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'cases': rows, 'limits': ['Scores identify artwork candidates only; no runtime admission.',
                                      'Per-channel normalization is diagnostic and does not qualify lighting.']}
    (output / 'review.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps([{'case': row['label'], 'best': row['best_diagnostic_match'],
                       'margin': row['diagnostic_rmse_margin']} for row in rows]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.report, args.output)
