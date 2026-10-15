"""Compare real occupancy to same-camera support-only native captures."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageFilter


def analyze(report_path, output):
    report = json.loads(report_path.read_bytes())
    if not all(report.get(key) for key in ('completed', 'restored', 'source_unchanged')):
        raise ValueError('The diagnostic must finish and restore its state')
    if report.get('cleanup_errors'):
        raise ValueError('The diagnostic has cleanup errors')
    results = {}
    for view in ('high', 'low'):
        records = [report['captures']['missing_' + view + '_' + state]
                   for state in ('occupied', 'support_control')]
        if records[0]['before']['camera'] != records[1]['before']['camera']:
            raise ValueError('Occupancy and support control cameras differ')
        images = []
        for record in records:
            capture = record['capture']
            path = Path(capture['path'])
            if not capture.get('reliable') or hashlib.sha256(path.read_bytes()).hexdigest() != capture['sha256']:
                raise ValueError('Unreliable or changed native capture')
            with Image.open(path) as source:
                images.append(source.convert('RGB'))
        if images[0].size != images[1].size:
            raise ValueError('Capture dimensions differ')
        width, height = images[1].size
        roi = (width//2-220, height//2-200, width//2+220, height//2+230)
        control = images[1].crop(roi)
        # Neutral support interiors avoid sky, silhouettes, and edge antialiasing.
        mask = Image.new('L', control.size)
        mask.putdata([255 if abs(pixel[0]-pixel[1]) <= 2 and 0 <= pixel[0]-pixel[2] <= 16
                      and 45 <= min(pixel) <= 220 else 0
                      for pixel in control.getdata()])
        mask = mask.filter(ImageFilter.MinFilter(5))
        differences = ImageChops.difference(images[0].crop(roi), control)
        values = [max(pixel) for pixel, included in zip(differences.getdata(), mask.getdata()) if included]
        if len(values) < 1000:
            raise ValueError('Too few interior support pixels')
        results[view] = {'same_camera': True, 'roi': roi, 'support_pixels': len(values),
                         'max_channel_difference': max(values),
                         'pixels_difference_over_8': sum(value > 8 for value in values),
                         'capture_sha256': [record['capture']['sha256'] for record in records]}
    result = {'schema': 1, 'product_qualified': False,
              'report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
              'method': 'Same-camera neutral support interior, 2-pixel erosion; no image resampling.',
              'scope': 'Detects occupied bottom residue; visual review must separately assess the shown seam.',
              'views': results}
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps(result))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    analyze(args.report, args.output)
