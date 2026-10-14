"""Detect isolated raster speckles inside the native brown book-cover artwork.

This narrow regression is independent of book pose, brightness and body-height
acceptance. Use an unobscured close-up and inspect the image alongside its score.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image

MAX_ISOLATED_PIXELS = 8
MIN_ARTWORK_PIXELS = 8000
MAX_DARK_FRACTION_DEVIATION = .15


def cover_pixels(image):
    r, g, b = np.moveaxis(image, -1, 0)
    return (r > g*1.25) & (g > b*1.3) & (g > 25) & (r < 220)


def isolated_cover_pixels(image):
    image = np.asarray(image, dtype=np.int16)
    center = image[1:-1, 1:-1]
    neighbors = np.stack((image[:-2, 1:-1], image[2:, 1:-1],
                          image[1:-1, :-2], image[1:-1, 2:]))
    # Texture regions and diagonals may change color; the failure consists of
    # individual fragments with a different color inside a uniform region.
    agree = np.max(np.ptp(neighbors, axis=0), axis=2) <= 3
    contrast = np.max(abs(center-neighbors.mean(axis=0)), axis=2) >= 12
    return cover_pixels(center) & np.all(cover_pixels(neighbors), axis=0) & agree & contrast


def artwork_distribution(image):
    """Reject the inside face of the native cover, independent of its exposure.

    This close-up fixture uses native references at the same camera. The outer
    artwork has a narrow dark border; a wrongly culled inside face is mostly
    dark. Only sufficiently broad cover views can establish this distinction.
    """
    pixels = image[cover_pixels(image)]
    if len(pixels) < MIN_ARTWORK_PIXELS:
        return None
    luma = pixels @ np.array((.2126, .7152, .0722))
    return float(np.mean(luma < np.percentile(luma, 90) * .75))


def analyze(source, output):
    raw = source.read_bytes()
    report = json.loads(raw)
    rows = []
    for label, row in report['captures'].items():
        if 'enchanting' not in label or 'attached' in label:
            continue
        capture = row['capture']
        path = Path(capture['path'])
        image_bytes = path.read_bytes()
        if hashlib.sha256(image_bytes).hexdigest() != capture['sha256']:
            raise ValueError('Book image no longer matches its capture receipt: '+str(path))
        if not capture.get('reliable'):
            raise ValueError('Book capture is unreliable: '+str(path))
        with Image.open(path) as image:
            w, h = image.size
            bounds = (w//2-180, h//2-150, w//2+180, h//2+95)
            pixels = np.array(image.convert('RGB').crop(bounds), dtype=np.int16)
        count = int(isolated_cover_pixels(pixels).sum())
        rows.append({'label': label, 'crop': bounds, 'isolated_cover_pixels': count,
                     'cover_pixels': int(cover_pixels(pixels).sum()),
                     'artwork_dark_fraction': artwork_distribution(pixels),
                     'below_noise_limit': count <= MAX_ISOLATED_PIXELS,
                     'frame_qpc_100ns': capture['frame']['frame_qpc_100ns']})
    candidate = [row for row in rows if row['label'].startswith('candidate_')]
    elapsed = ((max(row['frame_qpc_100ns'] for row in candidate)-
                min(row['frame_qpc_100ns'] for row in candidate))/1e7) if candidate else 0.
    scale = bool(candidate) and max(row['cover_pixels'] for row in candidate) >= 2000
    valid = (report.get('completed') and report.get('restored') and report.get('source_unchanged')
             and not report.get('cleanup_errors') and len(candidate) >= 16 and elapsed >= 16.)
    native_artwork = [row['artwork_dark_fraction'] for row in rows
                      if row['label'].startswith('native_') and row['artwork_dark_fraction'] is not None]
    candidate_artwork = [row['artwork_dark_fraction'] for row in candidate
                         if row['artwork_dark_fraction'] is not None]
    artwork_valid = len(native_artwork) >= 2 and len(candidate_artwork) >= 6
    artwork_limits = ([max(0., min(native_artwork)-MAX_DARK_FRACTION_DEVIATION),
                       min(1., max(native_artwork)+MAX_DARK_FRACTION_DEVIATION)]
                      if artwork_valid else None)
    artwork_passed = bool(artwork_valid and all(artwork_limits[0] <= value <= artwork_limits[1]
                                               for value in candidate_artwork))
    surface_passed = bool(valid and scale and all(row['below_noise_limit'] for row in candidate))
    result = {'schema': 1, 'source': str(source), 'source_sha256': hashlib.sha256(raw).hexdigest(),
              'analyzer_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'scope': 'Cover fragments and native outside/inside artwork distribution; pose, silhouette, occlusion and brightness need separate checks.',
              'requires_unobscured_fixture_review': True, 'product_qualified': False,
              'timeline_valid': bool(valid), 'scale_valid': scale, 'candidate_duration_seconds': elapsed,
              'maximum_isolated_pixels': MAX_ISOLATED_PIXELS, 'rows': rows,
              'artwork_reference_valid': artwork_valid, 'artwork_dark_fraction_limits': artwork_limits,
              'artwork_distribution_passed': artwork_passed,
              'surface_regression_passed': surface_passed,
              'raster_regression_passed': surface_passed and artwork_passed}
    output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii')
    print(json.dumps({key: result[key] for key in ('timeline_valid', 'surface_regression_passed',
                                                  'artwork_distribution_passed', 'raster_regression_passed')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.source, args.output)
