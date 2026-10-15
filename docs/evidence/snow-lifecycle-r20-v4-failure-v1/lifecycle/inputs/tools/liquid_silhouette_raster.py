"""Independent perspective depth comparison for declared full-cube neighbors."""
import math

import numpy as np
from PIL import Image

from measure_native_liquid_surface import pixel_viewport, projected_pixels

CUBE_FACES = ((4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6),
              (3, 0, 4, 7), (1, 2, 6, 5), (3, 2, 1, 0))


def cube_polygons(positions):
    for x, y, z in positions:
        points = tuple((x + dx, y + dy, z + dz) for dy in (0, 1)
                       for dx, dz in ((0, 0), (1, 0), (1, 1), (0, 1)))
        for corners in CUBE_FACES:
            yield tuple(points[index] for index in corners)


def depth_buffer(polygons, camera):
    """Nearest positive view depth, sampled at fixed pixel centers without fitting."""
    width, height = camera['native_image_screen']
    buffer = np.full((height, width), np.inf, dtype=np.float64)
    viewport = pixel_viewport(camera)
    for polygon in polygons:
        points = projected_pixels(polygon, camera, viewport)
        if any(point['depth'] < .05 or not point['isInScreen'] for point in points):
            raise ValueError('Declared occlusion geometry must lie completely inside the viewport')
        for corner in range(1, len(points) - 1):
            triangle = [points[index] for index in (0, corner, corner + 1)]
            x, y, inverse = (np.array([point[name] for point in triangle], dtype=np.float64)
                             for name in ('screenX', 'screenY', 'depth'))
            inverse = 1. / inverse
            area = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(area) < 1e-10:
                continue
            left, right = max(0, math.floor(min(x))), min(width, math.ceil(max(x)))
            top, bottom = max(0, math.floor(min(y))), min(height, math.ceil(max(y)))
            px, py = np.meshgrid(np.arange(left, right) + .5, np.arange(top, bottom) + .5)
            first = ((y[1] - y[2]) * (px - x[2]) + (x[2] - x[1]) * (py - y[2])) / area
            second = ((y[2] - y[0]) * (px - x[2]) + (x[0] - x[2]) * (py - y[2])) / area
            third = 1. - first - second
            inside = (first >= -1e-9) & (second >= -1e-9) & (third >= -1e-9)
            reciprocal = first * inverse[0] + second * inverse[1] + third * inverse[2]
            incoming = np.full_like(reciprocal, np.inf)
            np.divide(1., reciprocal, out=incoming, where=inside)
            current = buffer[top:bottom, left:right]
            np.minimum(current, incoming, out=current)
    return buffer


def visible_liquid_mask(liquid_polygons, blockers, camera):
    liquid = depth_buffer(liquid_polygons, camera)
    solid = depth_buffer(cube_polygons(blockers), camera)
    visible = np.isfinite(liquid) & (liquid < solid - 1e-7)
    return Image.fromarray(np.where(visible, 255, 0).astype(np.uint8))
