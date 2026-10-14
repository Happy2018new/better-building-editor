"""Check a frozen book cover against selected real blocks behind it.

The explicit ROI and brown cover mask exclude the HUD, background and silhouette.
An unchanged repeat proves the pose is stable. The depth-off negative control
must reproduce the leak before the depth-on image can pass this regression.
This checks opaque cover interiors, not complete rendering qualification.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def cover_mask(pixels, region):
    left, top, right, bottom = region
    height, width = pixels.shape[:2]
    if not 0 <= left < right <= width or not 0 <= top < bottom <= height:
        raise ValueError('Cover ROI is outside the capture')
    mask = np.zeros((height, width), dtype=bool)
    crop = pixels[top:bottom, left:right].astype(float)
    mask[top:bottom, left:right] = ((crop[:, :, 0] > crop[:, :, 1]*1.3) &
                                   (crop[:, :, 1] > crop[:, :, 2]*1.5))
    return np.asarray(Image.fromarray(mask.astype('uint8')*255).filter(
        ImageFilter.MinFilter(5))) > 0


def changes(first, second, mask):
    if first.shape != second.shape:
        raise ValueError('Capture size changed during the paired test')
    delta = np.max(np.abs(first.astype(int)-second.astype(int)), axis=2)
    return {'pixels': int(np.count_nonzero(mask & (delta > 8))),
            'maximum_channel_difference': int(delta[mask].max())}


def analyze(folder, case, region, output, mask_kind='cover'):
    report_path = folder/'report.json'
    report = json.loads(report_path.read_bytes())
    if not report.get('completed') or not report.get('restored'):
        raise ValueError('Capture matrix is incomplete or restoration failed')
    output.mkdir(parents=True, exist_ok=False)
    receipts, crops, rows, failures = {}, {}, {}, []

    def read(label):
        capture = report['captures'][label]['capture']
        if not capture.get('ok') or not capture.get('reliable'):
            raise ValueError('Unreliable capture: '+label)
        path = folder/(label+'.png')
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != capture['sha256']:
            raise ValueError('Capture bytes changed: '+label)
        receipts[label] = digest
        with Image.open(path) as source:
            rgb = source.convert('RGB')
        # Preserve exact pixel crops, never a reconstructed rendering.
        crop_path = output/(label+'.png')
        rgb.crop(region).save(crop_path)
        crops[crop_path.name] = hashlib.sha256(crop_path.read_bytes()).hexdigest()
        return np.asarray(rgb)

    for mode in ('off', 'on'):
        prefix = case+'_'+mode+'_'
        baseline = read(prefix+'air_back')
        mask = cover_mask(baseline, region)
        if mask_kind == 'rectangle':
            mask[:] = False
            left, top, right, bottom = region
            mask[top:bottom, left:right] = True
        count = int(mask.sum())
        if count < 100:
            raise ValueError('No useful opaque book cover inside the ROI')
        Image.fromarray(mask.astype('uint8')*255).save(output/(mode+'_mask.png'))
        repeat = changes(baseline, read(prefix+'air_back_repeat'), mask)
        rows[mode] = {'mask_pixels': count, 'repeat': repeat, 'backdrops': {}}
        if repeat['pixels']:
            failures.append(mode+': air repeat is unstable')
        for material in ('leaves', 'stone', 'glass'):
            label = prefix+material+'_back'
            pick = report['captures'][label]['pointed_block']
            hit = pick['hit']
            expected = 'minecraft:'+('oak_leaves' if material == 'leaves' else material)
            focus = report['prepared']['focus']
            if (hit.get('type') != 'Block' or hit.get('x') != focus[0]+2 or
                    hit.get('z') != focus[2] or not pick.get('material') or
                    pick['material'][0] != expected):
                raise ValueError('The real rear block was not selected: '+label)
            difference = changes(baseline, read(label), mask)
            rows[mode]['backdrops'][material] = dict(difference, selected=pick)
            if mode == 'off' and difference['pixels'] < 3:
                failures.append(label+': negative control did not reproduce the line')
            if mode == 'on' and difference['pixels']:
                failures.append(label+': selected rear block changed the opaque cover')
    result = {'schema_version': 1, 'passed': not failures, 'failures': failures,
              'scope': 'Frozen opaque surface interior; no product admission.',
              'case': case, 'mask_kind': mask_kind, 'region': list(region), 'pixel_threshold': 8,
              'source': report['rows'][case]['source'],
              'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
              'capture_sha256': receipts, 'crop_sha256': crops, 'results': rows}
    (output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--case', default='enchanting_table')
    parser.add_argument('--region', nargs=4, type=int, required=True)
    parser.add_argument('--mask-kind',choices=('cover','rectangle'),default='cover',
                        help='Rectangle must lie wholly inside an opaque surface, verified visually.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.input, args.case, args.region, args.output, args.mask_kind)
    print(json.dumps({'passed': result['passed'], 'failures': result['failures'],
                      'results': result['results']}))
    raise SystemExit(0 if result['passed'] else 1)
