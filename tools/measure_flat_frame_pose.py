"""Measure item depth at a fixed bitmap size from calibrated native views."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

from camera_projection import project_points
from verify_debug_blueprints import write_json
from verify_snow_plant_visibility import count

ROOT = Path(__file__).resolve().parents[1]


def predict(texture, size_pixels, depth_pixels, base, row, screen, fov, crop):
    width, height = texture.size
    polygons = []
    for y in range(height):
        for x in range(width):
            if not texture.getpixel((x, y)):
                continue
            polygons.append([(base[0] + .5 - size_pixels / 16. * (u / float(width) - .5),
                              base[1] + .5 + size_pixels / 16. * (.5 - v / float(height)),
                              base[2] + depth_pixels / 16.)
                             for u, v in ((x, y), (x + 1, y), (x + 1, y + 1), (x, y + 1))])
    points = project_points([point for polygon in polygons for point in polygon],
                            row['pose']['position'], row['pose']['target'], screen, fov)
    result = Image.new('L', (crop[2] - crop[0], crop[3] - crop[1]))
    draw = ImageDraw.Draw(result)
    for index in range(0, len(points), 4):
        draw.polygon([(point['screenX'] - crop[0], point['screenY'] - crop[1])
                      for point in points[index:index + 4]], fill=255)
    return result


def values(center, radius, step):
    return [center + index * step for index in range(-int(round(radius / step)), int(round(radius / step)) + 1)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--size-pixels', type=float, default=8., help='Fixed model size; default preserves the original 8 pixels')
    args = parser.parse_args()
    if not 0 < args.size_pixels <= 16:
        parser.error('Size must be in (0,16]')
    probe = json.loads(args.input.read_text(encoding='utf8'))
    calibration_path = Path(probe['camera_calibration'])
    calibration = json.loads(calibration_path.read_text(encoding='utf8'))
    assert probe['completed'] and probe['restored'] and len(probe['rows']) >= 2
    assert all(row['stone']['passed'] and row['vanilla']['filled_input']['rotation'] == 0.
               and row['vanilla']['item_pixels'] >= 80 for row in probe['rows'])
    texture_path = ROOT / 'resource_pack/textures/items/preview_flat_minecraft_diamond_sword_0.png'
    texture = Image.open(texture_path).convert('RGBA').getchannel('A')
    rows = []
    for row in probe['rows']:
        mask = Image.open(row['vanilla']['mask']).convert('L')
        crop = (mask.width // 4, mask.height // 4, mask.width * 3 // 4, mask.height * 3 // 4)
        rows.append((row, mask.crop(crop), mask.size, crop))
    stages = []
    best = None
    for stage in range(3):
        if stage == 0:
            depths = values(8., 7.5, .5)
        elif stage == 1:
            depths = values(best['depth_pixels'], .75, .125)
        else:
            depths = values(best['depth_pixels'], .125, .03125)
        candidates = []
        for size in (args.size_pixels,):
            for depth in depths:
                if not 0 < size <= 16 or not 0 <= depth < 16:
                    continue
                overlaps = []
                for row, mask, screen, crop in rows:
                    predicted = predict(texture, size, depth, probe['fixture']['base'], row, screen,
                                        calibration['vertical_fov'], crop)
                    intersection = count(ImageChops.multiply(mask, predicted))
                    union = count(ImageChops.lighter(mask, predicted))
                    overlaps.append(intersection / float(max(1, union)))
                candidates.append({'size_pixels': size, 'depth_pixels': depth, 'view_iou': overlaps,
                                   'minimum_iou': min(overlaps), 'mean_iou': sum(overlaps) / len(overlaps)})
        candidates.sort(key=lambda value: (value['minimum_iou'], value['mean_iou']), reverse=True)
        best = candidates[0]
        stages.append({'stage': stage, 'candidates': len(candidates), 'best': best, 'nearest': candidates[:5]})
    result = {'schema': 1, 'completed': True, 'production_rendering_accepted': False,
              'scope': 'World-space depth only; fixed bitmap size, logical X/Y center and native camera; no screen offsets or resizing',
              'input': str(args.input), 'input_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
              'camera_sha256': hashlib.sha256(calibration_path.read_bytes()).hexdigest(),
              'texture_sha256': hashlib.sha256(texture_path.read_bytes()).hexdigest(),
              'best': best, 'stages': stages}
    result['predictions'] = []
    for row, mask, screen, crop in rows:
        predicted = predict(texture, best['size_pixels'], best['depth_pixels'], probe['fixture']['base'],
                            row, screen, calibration['vertical_fov'], crop)
        path = args.output.with_name(args.output.stem + '_' + row['view'] + '_comparison.png')
        Image.merge('RGB', (mask, predicted, Image.new('L', mask.size))).save(path)
        result['predictions'].append(str(path))
    write_json(args.output, result)
    print(json.dumps(result['best']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
