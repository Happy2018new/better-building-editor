"""Preserve matched native/candidate shelf views without granting admission."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

VIEWS = ('south', 'east', 'north', 'west')
MODES = ('world', 'empty', 'live', 'roundtrip', 'prepared', 'proxy')


def shadow_pixels(enabled, disabled):
    first, second = (np.asarray(picture, dtype=np.int16) for picture in (enabled, disabled))
    if first.shape != second.shape or first.ndim != 3 or first.shape[2] != 3:
        raise ValueError('Shadow controls require matching RGB images')
    support = np.ones(first.shape[:2], dtype=bool)
    for sample in (first, second):
        red, green, blue = (sample[:, :, channel] for channel in range(3))
        support &= (green > red*1.8) & (blue > red*1.8) & (blue > green*.8) & (blue < green*1.3)
    # Erode the support mask to exclude changed edge coverage and background.
    interior = support.copy()
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            interior &= np.roll(np.roll(support, dy, axis=0), dx, axis=1)
    interior[:2] = interior[-2:] = False
    interior[:, :2] = interior[:, -2:] = False
    delta = second-first
    darkened = interior & (np.mean(delta, axis=2) > 12) & (np.min(delta, axis=2) >= 0)
    return {'support_interior_pixels': int(np.count_nonzero(interior)),
            'shadow_darkened_pixels': int(np.count_nonzero(darkened)),
            'maximum_channel_change': int(np.max(np.abs(delta[interior]))) if np.any(interior) else 0}


def capture_pixels(report, label, bounds):
    receipt = report['captures'][label]
    path = Path(receipt['path'])
    if not path.is_file():
        path = report['_report_directory']/path.name
    if receipt.get('reliable') is not True:
        raise ValueError('Unreliable shelf capture: '+label)
    if hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256']:
        raise ValueError('Shelf capture changed: '+label)
    with Image.open(path) as picture:
        if picture.size != (1994, 1105):
            raise ValueError('Review bounds require the recorded native window size')
        return path, picture.convert('RGB').crop(bounds)


def analyze(source, output):
    report = json.loads(source.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Shelf diagnostic did not complete with restoration and unchanged sources')
    if report.get('cleanup_errors') != []:
        raise ValueError('Shelf diagnostic contains cleanup errors')
    if output.exists():
        raise ValueError('Choose a fresh shelf review directory')
    output.mkdir(parents=True)
    report['_report_directory'] = source.parent
    rows = []
    pixels = {}
    # Native pixels stay unscaled, including the support and thin side profile.
    bounds = (800, 350, 1200, 930)
    sheet = Image.new('RGB', (len(MODES)*400, len(VIEWS)*604), '#252525')
    draw = ImageDraw.Draw(sheet)
    for y, view in enumerate(VIEWS):
        for x, mode in enumerate(MODES):
            label = mode+'_'+view
            receipt = report['captures'][label]
            path, crop = capture_pixels(report, label, bounds)
            destination = output/(label+'.png')
            crop.save(destination)
            pixels[label] = np.asarray(crop)
            draw.text((x*400+4, y*604+5), label, fill='white')
            sheet.paste(crop, (x*400, y*604+24))
            rows.append({'label': label, 'source': str(path), 'bounds': list(bounds),
                         'source_sha256': receipt['sha256'],
                         'crop_sha256': hashlib.sha256(destination.read_bytes()).hexdigest()})
    sheet.save(output/'review.png')
    shadows = {}
    if any(label.startswith('shadow_') for label in report['captures']):
        shadow_sheet = Image.new('RGB', (800, len(VIEWS)*604), '#252525')
        shadow_draw = ImageDraw.Draw(shadow_sheet)
        for y, view in enumerate(VIEWS):
            pair = []
            for x, enabled in enumerate((True, False)):
                label = ('shadow_on_' if enabled else 'shadow_off_')+view
                if report['captures'][label].get('entity_shadow_enabled') is not enabled:
                    raise ValueError('Shadow control flag is missing or inconsistent: '+label)
                unused, crop = capture_pixels(report, label, bounds)
                crop.save(output/(label+'.png'))
                shadow_draw.text((x*400+4, y*604+5), label, fill='white')
                shadow_sheet.paste(crop, (x*400, y*604+24))
                pair.append(crop)
            if report['captures']['shadow_on_'+view]['before'] != report['captures']['shadow_off_'+view]['before']:
                raise ValueError('Shadow controls use different cameras: '+view)
            shadows[view] = shadow_pixels(*pair)
        shadow_sheet.save(output/'shadow-review.png')
    silhouettes = {}
    for view in VIEWS:
        empty = pixels['empty_'+view].astype(np.int16)
        masks = {}
        for mode in ('world', 'proxy'):
            sample = pixels[mode+'_'+view].astype(np.int16)
            red, green, blue = (sample[:, :, channel] for channel in range(3))
            changed = np.max(np.abs(sample-empty), axis=2) > 12
            masks[mode] = changed & (red > green*1.04) & (green > blue*1.15) & (green > 20)
        native, candidate = masks['world'], masks['proxy']
        union = np.count_nonzero(native | candidate)
        silhouettes[view] = {'native_pixels': int(np.count_nonzero(native)),
                             'candidate_pixels': int(np.count_nonzero(candidate)),
                             'unshifted_iou': float(np.count_nonzero(native & candidate))/union if union else 0.}
    result = {'schema_version': 1, 'engine_version': '3.10.0.420447',
              'report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'captures': rows, 'silhouette_diagnostics': silhouettes, 'production_qualified': False,
              'shadow_controls': shadows,
              'limits': ['Matched camera native pixels only; no powered/connected state or item-content admission.']}
    (output/'review.json').write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps({'captures': len(rows), 'production_qualified': False}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.report, args.output)
