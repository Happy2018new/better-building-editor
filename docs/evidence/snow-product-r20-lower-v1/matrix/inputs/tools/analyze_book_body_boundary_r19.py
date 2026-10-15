"""Fail closed on native occupied table faces, with old-route pixel controls."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

FACES = ('down', 'north', 'south', 'east', 'west')
STATES = ('shown', 'occupied', 'support_control', 'blank', 'legacy_negative', 'restored')
MAX_CHANNEL_DIFFERENCE = 8
MIN_FACE_PIXELS = 100
MIN_NEGATIVE_PIXELS = 20
MIN_SUPPORT_PIXELS = 100


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def count(mask):
    return sum(mask.histogram()[1:])


def maximum(image):
    red, green, blue = image.split()
    return ImageChops.lighter(ImageChops.lighter(red, green), blue)


def changed(first, second, threshold=MAX_CHANNEL_DIFFERENCE):
    return maximum(ImageChops.difference(first, second)).point(
        lambda value: 255 if value > threshold else 0)


def hull(points):
    points = sorted(set(points))
    if len(points) < 3:
        raise ValueError('Native projected face has no area')
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    halves = []
    for sequence in (points, list(reversed(points))):
        half = []
        for point in sequence:
            while len(half) >= 2 and cross(half[-2], half[-1], point) <= 0:
                half.pop()
            half.append(point)
        halves.append(half[:-1])
    return halves[0]+halves[1]


def polygon_mask(size, points):
    if not points or not all(point.get('isInScreen') is True for point in points):
        raise ValueError('Native table boundary ROI is outside the captured viewport')
    coordinates = [(point['screenX'], point['screenY']) for point in points]
    if any(not (0 <= x < size[0] and 0 <= y < size[1]) for x, y in coordinates):
        raise ValueError('Native physical pixels do not fit the capture')
    mask = Image.new('L', size)
    ImageDraw.Draw(mask).polygon(hull(coordinates), fill=255)
    return mask


def measure_view(images, face_mask, support_mask, face):
    """Every comparison uses the same real occupied world and exact native pixels."""
    face_mask = face_mask.filter(ImageFilter.MaxFilter(3))
    support_signal = ImageChops.multiply(
        changed(images['support_control'], images['blank'], 16), support_mask)
    face_pixels = count(face_mask)
    support_pixels = count(support_signal)
    residue = count(ImageChops.multiply(
        changed(images['occupied'], images['support_control']), face_mask))
    negative = count(ImageChops.multiply(
        changed(images['legacy_negative'], images['support_control']), face_mask))
    support_lost = count(ImageChops.multiply(
        changed(images['occupied'], images['support_control']), support_signal))
    restored = count(ImageChops.multiply(
        changed(images['restored'], images['shown']), face_mask))
    shown = count(ImageChops.multiply(
        changed(images['shown'], images['support_control']), face_mask))
    gates = {'boundary_roi_present': face_pixels >= MIN_FACE_PIXELS,
             'occupied_face_removed': residue == 0,
             'legacy_residue_detected': negative >= MIN_NEGATIVE_PIXELS,
             'support_visible': support_pixels >= MIN_SUPPORT_PIXELS,
             'support_retained': support_lost == 0,
             'body_restored': restored == 0,
             'body_shown': shown >= MIN_FACE_PIXELS}
    return {'face_pixels': face_pixels, 'occupied_changed_pixels': residue,
            'legacy_negative_changed_pixels': negative, 'support_pixels': support_pixels,
            'support_changed_pixels': support_lost, 'restored_changed_pixels': restored,
            'shown_changed_pixels': shown, 'gates': gates, 'passed': all(gates.values())}


def load_images(records):
    images, camera = {}, None
    for state in STATES:
        record = records[state]
        before, after = record['before'], record['after']
        signature = [before[key] for key in ('camera', 'rotation', 'screen', 'engine')]
        if signature != [after[key] for key in ('camera', 'rotation', 'screen', 'engine')]:
            raise ValueError('Native camera or viewport changed during a boundary capture')
        if camera is not None and camera != signature:
            raise ValueError('Table boundary comparisons require the exact same camera')
        camera = signature
        capture = record['capture']
        path = Path(capture['path'])
        if capture.get('reliable') is not True or sha(path) != capture.get('sha256'):
            raise ValueError('Unreliable or changed native boundary capture')
        with Image.open(path) as source:
            images[state] = source.convert('RGB')
    if len({image.size for image in images.values()}) != 1:
        raise ValueError('Native boundary capture dimensions differ')
    return images


def analyze(report_path, output=None):
    report = json.loads(report_path.read_bytes())
    if (report.get('schema_version') != 1 or report.get('stage') != 'body_boundary_pixels' or
            report.get('engine') != '3.10.0.420447' or
            any(report.get(key) is not True for key in ('completed', 'restored', 'source_unchanged')) or
            report.get('cleanup_errors') != [] or set(report.get('views', {})) != set(FACES) or
            report.get('negative_route') != 'legacy_neighbor_context'):
        raise ValueError('Table boundary evidence is incomplete or lacks its native negative route')
    views = {}
    for face in FACES:
        row = report['views'][face]
        if (row.get('occupied_world_retained_for_controls') is not True or
                any(row['visibility'][state] != [expected, expected]
                    for state, expected in (('shown', 1), ('occupied', 0), ('restored', 1)))):
            raise ValueError('Table boundary captures lack stable real occupancy readbacks')
        images = load_images(row['captures'])
        size = images['shown'].size
        face_mask = polygon_mask(size, row['projection']['face'])
        target = polygon_mask(size, row['projection']['target']).filter(ImageFilter.MaxFilter(7))
        support = Image.new('L', size)
        for points in row['projection']['supports']:
            support = ImageChops.lighter(support, polygon_mask(size, points))
        support = ImageChops.subtract(support, target).filter(ImageFilter.MinFilter(3))
        views[face] = measure_view(images, face_mask, support, face)
    result = {'schema_version': 1, 'engine': report['engine'], 'product_qualified': False,
              'report_sha256': sha(report_path), 'analyzer_sha256': sha(Path(__file__)),
              'body_boundary_pixels_passed': all(row['passed'] for row in views.values()),
              'thresholds': {'max_channel_difference': MAX_CHANNEL_DIFFERENCE,
                             'allowed_changed_pixels': 0, 'min_negative_pixels': MIN_NEGATIVE_PIXELS,
                             'min_support_pixels': MIN_SUPPORT_PIXELS},
              'method': 'Exact physical native pixels; target face plus 1-pixel guard; '
                        'real stone retained in occupied/control/negative/blank; '
                        'support signal outside the target is measured against blank.',
              'views': views}
    if output is not None:
        output.write_text(json.dumps(result, indent=2)+'\n', encoding='ascii', newline='\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('report', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.report, args.output)))
