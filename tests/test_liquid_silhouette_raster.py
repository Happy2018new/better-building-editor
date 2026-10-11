"""Depth control distinguishes a held neighbor in front from one behind."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from liquid_silhouette_raster import cube_polygons, depth_buffer, visible_liquid_mask

CAMERA = {'position': [.5, .5, -4.], 'target': [.5, .5, .5],
          'screen': [400., 300.], 'native_image_screen': [400, 300], 'vertical_fov': 60.}


class LiquidSilhouetteRasterTests(unittest.TestCase):
    def test_front_neighbor_occludes_and_rear_neighbor_keeps_liquid_visible(self):
        no_neighbor = visible_liquid_mask(cube_polygons([(0, 0, 0)]), [], CAMERA)
        behind = visible_liquid_mask(cube_polygons([(0, 0, 0)]), [(0, 0, 1)], CAMERA)
        in_front = visible_liquid_mask(cube_polygons([(0, 0, 0)]), [(0, 0, -1)], CAMERA)
        self.assertGreater(no_neighbor.histogram()[255], 100)
        self.assertEqual(no_neighbor.tobytes(), behind.tobytes())
        self.assertEqual(0, in_front.histogram()[255])

    def test_nearest_depth_is_independent_of_face_and_object_iteration_order(self):
        polygons = list(cube_polygons([(0, 0, 0), (0, 0, -1)]))
        first, second = (depth_buffer(items, CAMERA) for items in (polygons, reversed(polygons)))
        np.testing.assert_array_equal(first, second)
        self.assertAlmostEqual(3., first[150, 200])

    def test_offscreen_or_near_clipped_geometry_is_not_silently_cropped(self):
        with self.assertRaises(ValueError):
            depth_buffer(cube_polygons([(100, 0, 0)]), CAMERA)
