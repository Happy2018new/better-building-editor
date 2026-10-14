"""Compare visible lectern page surfaces with a stable native close-up.

No alignment, recoloring or rescaling is applied to earn parity. The result
does not cover all book poses, the lectern body or production lifecycle.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


def page_mask(image):
    r, g, b = np.moveaxis(image, -1, 0)
    return (r > g*1.02) & (g > b*1.08) & (r < g*1.5) & (g < b*1.6) & (g > 100)


def compare(reference, candidate, tolerance=3):
    a, b = page_mask(reference), page_mask(candidate)
    if min(int(a.sum()), int(b.sum())) < 2000:
        return {'passed': False, 'reason': 'Insufficient visible page surface'}
    def expand(mask):
        return np.asarray(Image.fromarray(mask).filter(ImageFilter.MaxFilter(2*tolerance+1)))
    precision = float((b & expand(a)).sum()) / b.sum()
    recall = float((a & expand(b)).sum()) / a.sum()
    native_rgb, candidate_rgb = np.median(reference[a], axis=0), np.median(candidate[b], axis=0)
    color_delta = float(np.max(abs(native_rgb-candidate_rgb)))
    return {'precision': precision, 'recall': recall,
            'native_median_rgb': native_rgb.tolist(), 'candidate_median_rgb': candidate_rgb.tolist(),
            'maximum_color_delta': color_delta, 'tolerance_pixels': tolerance,
            'native_page_pixels': int(a.sum()), 'candidate_page_pixels': int(b.sum()),
            'passed': bool(precision >= .98 and recall >= .98 and color_delta <= 8.)}


def analyze(source, output):
    report = json.loads(source.read_bytes())
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged')) or report.get('cleanup_errors'):
        raise ValueError('Book comparison did not complete and restore')
    selected = {label: row for label, row in report['captures'].items() if 'lectern.book_motion' in label}
    native = [label for label in selected if label.startswith('native_')]
    candidate = [label for label in selected if label.startswith('candidate_')]
    if len(native) < 2 or len(candidate) < 2:
        raise ValueError('Need repeated native and candidate close-ups')
    images, camera, captures = {}, None, {}
    for label, row in selected.items():
        for state in (row['before'], row['after']):
            signature = {key: state[key] for key in ('camera', 'rotation', 'screen', 'foot')}
            if camera is None:
                camera = signature
            if signature != camera:
                raise ValueError('Native and candidate camera/foot must match: ' + label)
        capture = row['capture']
        path = Path(capture['path'])
        if not capture.get('reliable') or hashlib.sha256(path.read_bytes()).hexdigest() != capture['sha256']:
            raise ValueError('Invalid book capture: ' + label)
        with Image.open(path) as image:
            w, h = image.size
            bounds = (w//2-180, h//2-150, w//2+180, h//2+95)
            images[label] = np.asarray(image.convert('RGB').crop(bounds), dtype=float)
        captures[label] = {'source': str(path), 'source_sha256': capture['sha256'], 'crop': bounds}
    reference = images[native[0]]
    stability = [compare(reference, images[label], 0) for label in native[1:]]
    comparisons = {label: compare(reference, images[label]) for label in candidate}
    result = {'schema': 1, 'product_qualified': False,
              'scope': 'Stationary visible lectern page surface, color and boundary; no full book qualification.',
              'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'camera': camera, 'captures': captures,
              'native_stability': stability, 'candidates': comparisons,
              'page_surface_parity_passed': all(row['passed'] for row in stability+list(comparisons.values()))}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({'page_surface_parity_passed': result['page_surface_parity_passed'],
                      'candidates': comparisons}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.source, args.output)
