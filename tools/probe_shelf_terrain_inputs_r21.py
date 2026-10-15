"""Reuse the two-image acquisition with eight-slot terrain observations."""
from collections import Counter
import math

from PIL import Image

import probe_shelf_native_routes_r21 as routes
from prepare_shelf_terrain_inputs_r21 import STRIPES, verify


def pixel_observations(world, empty, projection):
    points = [row['screen'] for row in projection]
    with Image.open(world).convert('RGB') as first, Image.open(empty).convert('RGB') as second:
        if first.size != second.size:
            raise ValueError('The terrain input images have different dimensions')
        bounds = [max(0, int(math.floor(min(point['screenX'] for point in points)))-4),
                  max(0, int(math.floor(min(point['screenY'] for point in points)))-4),
                  min(first.width, int(math.ceil(max(point['screenX'] for point in points)))+4),
                  min(first.height, int(math.ceil(max(point['screenY'] for point in points)))+4)]
        if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
            raise ValueError('The projected terrain cell has no image area')
        slots = []
        for slot, name in enumerate(STRIPES):
            samples = [(x, y, first.getpixel((x, y)), second.getpixel((x, y)))
                       for y in range(bounds[1], bounds[3]) for x in range(bounds[0], bounds[2])
                       if x//16 % 8 == slot]
            changed = [row for row in samples if max(abs(a-b) for a, b in zip(row[2], row[3])) > 24]
            common = Counter(row[2] for row in changed)
            slots.append({'slot': slot, 'name': name, 'pixels': len(samples),
                'changed_pixels_gt_24': len(changed),
                'changed_common_rgb': [{'rgb': rgb, 'pixels': count} for rgb, count in common.most_common(12)],
                'first_changed_points': [{'x': row[0], 'y': row[1], 'world_rgb': row[2], 'empty_rgb': row[3]}
                                         for row in changed[:8]]})
        return {'bounds': bounds, 'slots': slots, 'native_input_readback_qualified': False,
            'production_qualified': False,
            'scope': 'Unsegmented projected ROI only. Root must identify shelf body and marker/data pairs before interpreting input values.'}


def main():
    routes.verify = verify
    routes.pixel_observations = pixel_observations
    routes.main()


if __name__ == '__main__':
    main()
