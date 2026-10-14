"""Produce review sheets and conservative color-presence checks for banners."""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def analyze(folder, output):
    report_path = folder / 'report.json'
    report = json.loads(report_path.read_bytes())
    rows, panels = {}, []
    for label, observation in report['captures'].items():
        path = Path(observation['capture']['path'])
        if not path.exists():
            path = folder / path.name
        if digest(path) != observation['capture']['sha256']:
            raise ValueError('Captured banner pixels changed: ' + label)
        im = Image.open(path).convert('RGB')
        if label.startswith('editor_'):
            box = tuple(round(value * im.width / 1994.) for value in (485, 355, 1525, 846))
            crop = im.crop(box)
            values = np.asarray(crop, dtype=np.int16)
            maximum, minimum = values.max(axis=2), values.min(axis=2)
            # Exclude thin bright blue selection edges and the small axis arrows.
            color = ((maximum - minimum > 65) & (minimum < 160) &
                     ~((values[:, :, 2] > 215) & (values[:, :, 0] < 130)))
            rows[label] = {'colored_pixels': int(color.sum()), 'crop': box}
        else:
            crop = im
            rows[label] = {'pixel_presence_manually_reviewed': False}
        panel = crop.copy()
        panel.thumbnail((720, 390))
        canvas = Image.new('RGB', (740, 420), '#e6e8eb')
        canvas.paste(panel, ((740-panel.width)//2, 28))
        ImageDraw.Draw(canvas).text((12, 8), label, fill='black')
        panels.append(canvas)
    output.mkdir(parents=True, exist_ok=True)
    sheets = []
    for offset in range(0, len(panels), 6):
        group = panels[offset:offset+6]
        canvas = Image.new('RGB', (1480, ((len(group)+1)//2)*420), 'white')
        for index, panel in enumerate(group):
            canvas.paste(panel, ((index%2)*740, (index//2)*420))
        path = output / ('review-%02d.png' % (offset//6))
        canvas.save(path)
        sheets.append({'name': path.name, 'sha256': digest(path)})
    result = {'schema': 1, 'report_sha256': digest(report_path), 'rows': rows, 'sheets': sheets,
              'limits': 'Color presence is a coarse diagnostic, not per-banner occlusion or motion qualification.',
              'manual_pixel_acceptance': False}
    (output/'analysis.json').write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({'captures': len(rows), 'sheets': len(sheets), 'output': str(output)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    analyze(args.folder, args.output)


if __name__ == '__main__':
    main()
