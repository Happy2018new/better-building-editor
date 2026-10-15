"""Preserve verified, unscaled crops of book/body diagnostics for review.

This retains the original report and hashes and never grants production
qualification. Full source captures remain at their recorded local paths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image, ImageDraw


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pack(source, output, mode):
    report = json.loads(source.read_bytes())
    if (not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged'))
            or report.get('cleanup_errors')):
        raise ValueError('Diagnostic must complete and restore before evidence packaging')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(source, output / 'report.json')
    captures = report.get('captures', {})
    boundary_bounds = {}
    if mode == 'boundary':
        from analyze_book_body_boundary_r19 import analyze
        if not analyze(source)['body_boundary_pixels_passed']:
            raise ValueError('Body boundary evidence has not passed its pixel controls')
        captures = {}
        for face, view in report['views'].items():
            points = view['projection']['target'] + [
                point for support in view['projection']['supports'] for point in support]
            for state, record in view['captures'].items():
                label = face + '_' + state
                captures[label] = record
                boundary_bounds[label] = (min(point['screenX'] for point in points),
                                           min(point['screenY'] for point in points),
                                           max(point['screenX'] for point in points),
                                           max(point['screenY'] for point in points))
    records, images = {}, []
    for label, record in captures.items():
        capture = record.get('capture', record)
        path = Path(capture['path'])
        if not capture.get('reliable') or digest(path) != capture['sha256']:
            raise ValueError('Invalid source capture: ' + str(path))
        with Image.open(path) as original:
            w, h = original.size
            if mode == 'boundary':
                left, top, right, bottom = boundary_bounds[label]
                bounds = (max(0, int(left)-16), max(0, int(top)-16),
                          min(w, int(right)+17), min(h, int(bottom)+17))
            elif mode == 'reference':
                bounds = (w//2-180, h//2-150, w//2+180, h//2+95)
            elif mode == 'body':
                bounds = (w//2-160, h//2-150, w//2+160, h//2+240)
            elif label.startswith('editor_'):
                bounds = (w//2-350, h//2-180, w//2+250, h//2+330)
            else:
                bounds = (w//2-300, h//2-270, w//2+300, h//2+240)
            crop = original.convert('RGB').crop(bounds)
        target = output / (label + '.png')
        crop.save(target)
        records[label] = {'source': str(path), 'source_sha256': capture['sha256'],
                          'bounds': bounds, 'crop_sha256': digest(target)}
        images.append((label, crop))
    for start in range(0, len(images), 6):
        batch = images[start:start+6]
        width = max(im.width for _, im in batch)
        height = max(im.height for _, im in batch) + 28
        sheet = Image.new('RGB', (width*3, height*2), '#222222')
        draw = ImageDraw.Draw(sheet)
        for index, (label, crop) in enumerate(batch):
            x, y = index % 3 * width, index // 3 * height
            draw.text((x+4, y+4), label, fill='white')
            sheet.paste(crop, (x, y+28))
        sheet.save(output / ('review-%02d.png' % (start//6)))
    (output / 'crops.json').write_text(json.dumps({
        'schema': 1, 'source_sha256': digest(source), 'product_qualified': False,
        'pixels': 'Exact crops; no scaling, enhancement or synthesized pixels.',
        'captures': records,
    }, indent=2) + '\n', encoding='ascii')
    for name in ('surface-analysis.json', 'analysis.json'):
        path = source.parent / name
        if path.is_file():
            shutil.copyfile(path, output / name)
    print(json.dumps({'captures': len(records), 'output': str(output)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--mode', choices=('reference', 'product', 'body', 'boundary'), required=True)
    args = parser.parse_args()
    pack(args.source, args.output, args.mode)
