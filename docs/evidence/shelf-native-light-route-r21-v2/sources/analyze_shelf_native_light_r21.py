"""Read fragment-only native shelf diagnostics at physical pixel coordinates."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_shelf_body_matrix_r20 import pixels


ROI = (140, 160, 240, 180)
NAMES = ('magenta_selector', 'native_light_rgb', 'tile_light_rgb', 'flags')


def sample_stripes(array, physical_origin_x):
    left, top, right, bottom = ROI
    if array.ndim != 3 or array.shape[2] != 3 or array.shape[0] < bottom or array.shape[1] < right:
        raise ValueError('Native shelf stripe crop is too small')
    sample = array[top:bottom, left:right]
    stripes = ((physical_origin_x + np.arange(left, right)) // 16) % 4
    rows = []
    for index, name in enumerate(NAMES):
        values = sample[:, stripes == index].reshape(-1, 3)
        if not len(values):
            raise ValueError('Fixed native shelf ROI must contain all four stripes')
        colors, counts = np.unique(values, axis=0, return_counts=True)
        order = np.argsort(counts)[::-1]
        row = {'stripe': index, 'name': name, 'pixels': len(values),
               'min_rgb': values.min(axis=0).tolist(), 'max_rgb': values.max(axis=0).tolist(),
               'top_colors': [{'rgb': colors[pos].tolist(), 'pixels': int(counts[pos])}
                              for pos in order[:8]]}
        if index == 0:
            row['selector_valid'] = bool(np.all(values == (255, 0, 255)))
        if index == 3:
            green = np.rint(np.arange(8) * 255. / 7.)
            row['flags_valid'] = bool(np.all(np.isin(values[:, 0], (0, 255))) and
                np.all(np.isin(values[:, 2], (0, 255))) and
                np.all(np.min(np.abs(values[:, 1, None] - green), axis=1) <= 1))
        rows.append(row)
    valid = rows[0]['selector_valid'] and rows[3]['flags_valid']
    return {'roi': list(ROI), 'physical_origin_x': physical_origin_x,
            'readback_valid': valid, 'stripes': rows}


def analyze(source, contract, output):
    report = json.loads(source.read_bytes())
    definition = json.loads(contract.read_bytes())
    if not all(report.get(key) is True for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('Native shelf readback must complete and restore unchanged sources')
    if report.get('cleanup_errors'):
        raise ValueError('Native shelf readback cleanup failed')
    if definition.get('vertex_shader_or_fields_changed') is not False or definition.get('stripes', {}).get('period_pixels') != 64:
        raise ValueError('Unchanged native vertex and 64-pixel stripe contract required')
    output.mkdir(parents=True, exist_ok=False)
    records, crops = [], []
    for case in report['cases']:
        label = case['label'] + '_world'
        array = pixels(report, label, source.parent)
        target = report['captures'][label]['before']['target_screen']
        row = sample_stripes(array, round(target['screenX'] - 190))
        row.update({'case': case['label'], 'capture_sha256': report['captures'][label]['sha256']})
        records.append(row)
        picture = Image.fromarray(array)
        draw = ImageDraw.Draw(picture)
        draw.rectangle(ROI, outline='yellow', width=1)
        picture.save(output / (label + '.png'))
        crops.append(picture)
    if not records:
        raise ValueError('No native shelf observations')
    sheet = Image.new('RGB', (380 * len(crops), 324), '#252525')
    draw = ImageDraw.Draw(sheet)
    for index, (row, picture) in enumerate(zip(records, crops)):
        draw.text((index * 380 + 4, 4), row['case'], fill='white')
        sheet.paste(picture, (index * 380, 24))
    sheet.save(output / 'native-light.png')
    result = {'schema': 1, 'production_qualified': False,
              'readback_valid': all(row['readback_valid'] for row in records),
              'source_report_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'contract_sha256': hashlib.sha256(contract.read_bytes()).hexdigest(),
              'records': records,
              'limits': ['Fixed central backing ROI only; no complete surface acceptance.',
                         'Still-textured native draws fail material selection.',
                         'No exposure correction, gain fit, alignment or lighting qualification.']}
    (output / 'native-light.json').write_text(json.dumps(result, indent=2) + '\n', encoding='ascii', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('contract', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.report, args.contract, args.output)
