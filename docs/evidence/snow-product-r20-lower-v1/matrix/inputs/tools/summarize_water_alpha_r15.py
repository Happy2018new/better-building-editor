"""Make inspectable, source-bound contact sheets for frozen water qualification."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from analyze_product_water import expected_mask


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.source.read_bytes())
    analysis = json.loads(args.analysis.read_bytes())
    if args.output.exists():
        parser.error('Choose a fresh summary')
    args.output.mkdir(parents=True)
    frames = {}
    for kind, controls in (('alpha', ('0', '0_25', '0_45', '0_75', '1', 'default')),
                           ('body', ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty'))):
        sheet = Image.new('RGB', (1080, 660), 'white')
        draw = ImageDraw.Draw(sheet)
        for row_index, route in enumerate(('editor', 'full', 'missing')):
            label = route + '_wet_oak_fence_wet'
            row = source['rows'][label]
            frame = source['captures'][label]
            shape = expected_mask(row, source, (frame['width'], frame['height']))
            yy, xx = np.nonzero(shape)
            if not len(xx):
                raise ValueError('Water crop requires an independently projected visible shape')
            crop = (max(0, int(xx.min()) - 24), max(0, int(yy.min()) - 28),
                    min(frame['width'], int(xx.max()) + 25), min(frame['height'], int(yy.max()) + 76))
            for col_index, control in enumerate(controls):
                name = (label + '_alpha_' + control if kind == 'alpha'
                        else route + '_wet_oak_fence_' + control)
                captured = source['captures'][name]
                path = Path(captured['path'])
                if digest(path) != captured['sha256']:
                    raise ValueError('Capture changed: ' + str(path))
                with Image.open(path) as image:
                    tile = image.convert('RGB').crop(crop)
                    tile.thumbnail((172, 192), Image.Resampling.NEAREST)
                    sheet.paste(tile, (col_index * 180 + (180 - tile.width) // 2,
                                       row_index * 220 + 22))
                draw.text((col_index * 180 + 5, row_index * 220 + 4), route + ' ' + control, fill='black')
                frames[name] = {'path': str(path.resolve()), 'sha256': captured['sha256'],
                                'crop': crop, 'native_size': (captured['width'], captured['height'])}
        sheet.save(args.output / (kind + '-contact.png'))
    summary = {'schema': 1, 'source_report_sha256': digest(args.source), 'analysis_sha256': digest(args.analysis),
               'completed': source['completed'], 'restored': source['restored'],
               'source_unchanged': source['source_unchanged'], 'source_contract_sha256': source['source_contract_sha256'],
               'frozen': source['frozen'], 'session_binding': source['session_binding'],
               'transparency': analysis['transparency'], 'alpha_controls': analysis['alpha_controls'],
               'evidence_valid': analysis['evidence_valid'], 'captures': frames,
               'scope': 'Three production owner paths at fixed phase; directional animation is separate'}
    (args.output / 'summary.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n', encoding='ascii')
    print(json.dumps({'evidence_valid': summary['evidence_valid'], 'captures': len(frames)}))


if __name__ == '__main__':
    main()
