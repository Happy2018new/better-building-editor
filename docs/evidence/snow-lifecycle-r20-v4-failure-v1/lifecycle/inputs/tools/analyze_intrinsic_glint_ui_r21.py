"""Compare paired native glint controls, retaining dynamic/unsupported ambiguity."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

DYNAMIC = frozenset(('minecraft:compass', 'minecraft:lodestone_compass',
                     'minecraft:recovery_compass', 'minecraft:clock'))
GLINT_COLOR = np.array((.38 ** 2 / .61 ** 2, .19 ** 2 / .61 ** 2, 1.))


def glint_signature(frames):
    """Fit additive purple modulation; reject moving needles and clipped RGB."""
    deltas, safe = [], []
    for before, after in zip(frames, frames[1:]):
        deltas.append(after.astype(np.float64) - before)
        safe.append((np.max(before, axis=2) > 48) &
                    (np.max(after, axis=2) > 48) &
                    (np.max(before, axis=2) < 249) &
                    (np.max(after, axis=2) < 249))
    values = np.stack(deltas)[np.stack(safe)]
    values = values[np.abs(values[:, 2]) > 5]
    if not len(values):
        return {'moving_samples': 0, 'matching_samples': 0, 'matching_fraction': 0.,
                'channel_ratios': None, 'residual_p95': None, 'detected': False}
    residual = np.max(np.abs(values - values[:, 2, None] * GLINT_COLOR), axis=1)
    matching = residual <= 2.5
    fitted = values[matching]
    ratios = ([float(np.dot(fitted[:, 2], fitted[:, channel]) /
                     np.dot(fitted[:, 2], fitted[:, 2])) for channel in (0, 1)]
              if len(fitted) else None)
    return {'moving_samples': len(values), 'matching_samples': int(np.count_nonzero(matching)),
            'matching_fraction': float(np.mean(matching)), 'channel_ratios': ratios,
            'residual_p95': float(np.percentile(residual, 95)),
            'detected': len(fitted) >= 64 and float(np.mean(matching)) >= .9}


def analyze(directory):
    report = json.loads((directory / 'report.json').read_text(encoding='ascii'))
    if not report['completed'] or report['cleanup_errors'] or not report['restoration']['restored']:
        raise ValueError('A completed, restored diagnostic page is required')
    prepared = report['prepared']
    arrays, images = [], []
    for capture in report['captures']:
        receipt = capture['receipt']
        path = directory / Path(receipt['path']).name
        if not receipt['reliable'] or hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
            raise ValueError('Missing, unreliable or changed native capture')
        images.append(Image.open(path).convert('RGB'))
        arrays.append(np.asarray(images[-1]).astype(np.int16))
    logical = prepared['screen']
    scale_x = round(images[0].width / logical[0])
    scale_y = round(images[0].height / logical[1])
    if scale_x != scale_y or min(scale_x, scale_y) < 1:
        raise ValueError('The diagnostic needs one stable integer GUI scale')
    scale = scale_x
    groups = {}
    for item in prepared['rows']:
        groups.setdefault(item['index'], {})[item['is_enchanted_argument']] = item
    rows, crops = [], []
    for index, items in sorted(groups.items()):
        if set(items) != {False, True}:
            raise ValueError('Every item must have a false/true pair')
        pixel_pairs, bounds = [], {}
        for flag, item in items.items():
            x, y, width, height = (round(value * scale) for value in item['bounds'])
            box = (x, y, x + width, y + height)
            if x < 0 or y < 0 or x + width > images[0].width or y + height > images[0].height:
                raise ValueError('A native item icon is clipped by the screenshot')
            bounds[str(flag)] = box
            pixel_pairs.append((flag, [array[y:y+height, x:x+width] for array in arrays]))
        packets = dict(pixel_pairs)
        false, true = packets[False], packets[True]
        # Dark backdrop differences are not evidence of a different item pass.
        mask = np.logical_or.reduce([np.max(value, axis=2) > 48 for value in false + true])
        pair_deltas = [np.max(np.abs(a - b), axis=2)[mask] for a, b in zip(false, true)]
        false_motion = [np.max(np.abs(a - b), axis=2)[mask] for a, b in zip(false, false[1:])]
        true_motion = [np.max(np.abs(a - b), axis=2)[mask] for a, b in zip(true, true[1:])]

        def metrics(values):
            joined = np.concatenate(values) if values else np.array([], dtype=np.int16)
            return {'maximum': int(joined.max()) if joined.size else 0,
                    'mean': float(joined.mean()) if joined.size else 0.,
                    'changed_over_3': int(np.count_nonzero(joined > 3)),
                    'samples': int(joined.size)}

        pair, unforced, forced = metrics(pair_deltas), metrics(false_motion), metrics(true_motion)
        unforced_signature, forced_signature = glint_signature(false), glint_signature(true)
        row = {'index': index, 'name': items[False]['name'], 'aux': items[False]['aux'],
               'real_ench_user_data': items[False]['real_ench_user_data'],
               'native_set_succeeded': all(item['set_returned'] is True for item in items.values()),
               'body_pixels': int(np.count_nonzero(mask)), 'physical_bounds': bounds,
               'paired_deltas': pair, 'unforced_temporal_deltas': unforced,
               'forced_temporal_deltas': forced, 'classification': 'unresolved',
               'unforced_glint_signature': unforced_signature,
               'forced_glint_signature': forced_signature,
               'visual_qualification': False}
        if not row['native_set_succeeded']:
            row['reason'] = 'Native item renderer rejected at least one paired request'
        elif unforced_signature['detected'] and forced_signature['detected']:
            row['classification'] = 'intrinsic_glint_native_confirmed'
            row['reason'] = 'Unforced temporal RGB modulation fits the controlled native purple glint signature'
        elif (forced_signature['detected'] and not unforced_signature['matching_samples'] and
              not unforced['changed_over_3']):
            row['classification'] = 'no_intrinsic_glint_in_this_probe'
            row['reason'] = 'Only the forced pass animates; actual item state is recorded'
        elif row['name'] in DYNAMIC:
            row['reason'] = 'Indicator motion is distinct from glint; preserve unresolved moving body pixels'
        else:
            row['reason'] = 'Pixel controls are insufficient; preserve the item as unresolved'
        rows.append(row)
        crops.append((images[0].crop(bounds['False']), images[0].crop(bounds['True'])))
    tile_width, tile_height = 390, 210
    sheet = Image.new('RGB', (tile_width * 3, tile_height * ((len(rows) + 2) // 3)), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    for index, (row, (left, right)) in enumerate(zip(rows, crops)):
        x, y = index % 3 * tile_width, index // 3 * tile_height
        draw.text((x + 4, y + 3), row['name'] + ':' + str(row['aux']), fill='white')
        draw.text((x + 4, y + 18), row['classification'], fill='white')
        sheet.paste(left, (x + 8, y + 43))
        sheet.paste(right, (x + 200, y + 43))
    sheet.save(directory / 'paired-review.png')
    control_rows = rows[:prepared['control_count']] if prepared.get('control_count') else rows
    controls = [row for row in control_rows if row['name'] in ('minecraft:diamond_sword', 'minecraft:golden_apple',
                                                      'minecraft:stone')
                and not row['real_ench_user_data']]
    control_pass = (len(controls) >= 2 and all(
        not row['unforced_glint_signature']['detected'] and
        row['forced_glint_signature']['detected'] for row in controls))
    if not control_pass:
        for row in rows:
            row['classification'] = 'unresolved'
            row['reason'] = 'Required plain/forced native glint controls did not pass'
    result = {'schema': 2, 'report_sha256': hashlib.sha256((directory / 'report.json').read_bytes()).hexdigest(),
              'gui_scale': scale, 'rows': rows, 'production_qualified': False,
              'signature': {'normalized_squared_color': GLINT_COLOR.tolist(),
                            'maximum_channel_residual': 2.5, 'minimum_moving_samples': 64,
                            'minimum_matching_fraction': .9,
                            'nonclipped_channel_maximum': 248,
                            'minimum_blue_delta': 5},
              'native_controls_passed': control_pass,
              'conclusion': 'Native UI item behavior only; production editor/world pixels remain unqualified'}
    (directory / 'analysis.json').write_text(json.dumps(result, ensure_ascii=True, indent=2) + '\n', encoding='ascii')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    result = analyze(args.directory)
    print(json.dumps([{'name': row['name'], 'aux': row['aux'], 'status': row['classification'],
                       'pair_max': row['paired_deltas']['maximum'],
                       'plain_motion': row['unforced_temporal_deltas']['changed_over_3'],
                       'forced_motion': row['forced_temporal_deltas']['changed_over_3']}
                      for row in result['rows']]))
