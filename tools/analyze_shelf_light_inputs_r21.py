"""Inspect actual shelf GPU input bytes without color fitting or admission."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_shelf_body_matrix_r20 import pixels, cell_scope


def analyze(source, output):
    report = json.loads(source.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Input readback must complete and restore unchanged sources')
    if report.get('cleanup_errors'):
        raise ValueError('Input readback cleanup failed')
    inputs = report['shader_inputs']
    modes = sorted((int(mode), name) for mode, name in inputs['modes'].items())
    if inputs['marker'] != 19491. or not modes:
        raise ValueError('The actual shader input contract is required')
    output.mkdir(parents=True, exist_ok=False)
    records, strips = [], []
    for case in report['cases']:
        label = case['label']
        for control in ('shelf', 'stone'):
            samples = []
            for mode, name in modes:
                key = label+'_'+control+'_input_'+str(mode)
                array = pixels(report, key, source.parent)
                scope = cell_scope(report, case, array.shape)
                if scope is None:
                    raise ValueError('Native projected cell is required')
                center = array[160:180, 180:200]
                colors, counts = np.unique(center.reshape(-1, 3), axis=0, return_counts=True)
                order = np.argsort(counts)[::-1]
                records.append({'case': label, 'control': control, 'mode': mode, 'name': name,
                                'center_roi': [180, 160, 200, 180],
                                'center_top_colors': [{'rgb': colors[index].tolist(), 'pixels': int(counts[index])}
                                                      for index in order[:8]],
                                'center_min_rgb': center.min(axis=(0, 1)).tolist(),
                                'center_max_rgb': center.max(axis=(0, 1)).tolist(),
                                'capture_sha256': report['captures'][key]['sha256']})
                ys, xs = np.nonzero(scope)
                crop = Image.fromarray(array).crop((xs.min(), ys.min(), xs.max()+1, ys.max()+1))
                crop.save(output/(key+'.png'))
                samples.append((name, crop))
            strips.append((label+' / '+control, samples))
    width = max(crop.width for unused, samples in strips for unused, crop in samples)
    height = max(crop.height for unused, samples in strips for unused, crop in samples)+40
    sheet = Image.new('RGB', (width*len(modes), height*len(strips)), '#252525')
    draw = ImageDraw.Draw(sheet)
    for row, (label, samples) in enumerate(strips):
        for col, (name, crop) in enumerate(samples):
            point = (col*width, row*height)
            sheet.paste(crop, (point[0], point[1]+40))
            draw.text((point[0]+2, point[1]+2), label, fill='white')
            draw.text((point[0]+2, point[1]+18), name, fill='white')
    sheet.save(output/'inputs.png')
    flags = [row for row in records if row['mode'] == 7]
    flag_values = np.array([round(index*255./7.) for index in range(8)])
    for row in flags:
        top = row['center_top_colors'][0]
        rgb = np.array(top['rgb'])
        row['flag_readback_valid'] = bool(top['pixels'] == 400 and rgb[0] in (0, 255) and
            all(np.min(np.abs(flag_values-value)) <= 1 for value in rgb[1:]))
    result = {'production_qualified': False,
              'flag_readback_valid': bool(flags) and all(row['flag_readback_valid'] for row in flags),
              'shader_inputs': inputs,
              'source_report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'records': records,
              'limits': ['Center ROI is a fixed diagnostic sample, not complete surface acceptance',
                         'No color gain, alignment, lighting fit or brightness qualification']}
    (output/'inputs.json').write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    print(json.dumps(records))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.report, args.output)
