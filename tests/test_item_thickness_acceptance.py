"""Thin side controls must remain measurable and retain relative lighting errors."""
from pathlib import Path
import json
import sys
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_item_thickness_r20 import (appearance, eroded, side_comparison,
                                       side_surfaces, surface_appearance)


class ThicknessAcceptanceTests(unittest.TestCase):
    def test_blank_and_too_small_side_controls_cannot_pass(self):
        reference = np.zeros((64, 64), dtype=bool)
        reference[8:48, 15:18] = True
        self.assertTrue(side_comparison(reference, reference)['passed'])
        self.assertFalse(side_comparison(np.zeros_like(reference), reference)['passed'])
        self.assertFalse(side_comparison(np.roll(reference, 8, axis=1), reference)['passed'])
        reference[16:, :] = False
        self.assertFalse(side_comparison(reference, reference)['passed'])

    def test_one_pixel_interior_excludes_rasterization_boundaries(self):
        mask = np.zeros((11, 11), dtype=bool)
        mask[2:9, 2:9] = True
        interior = eroded(mask, 1)
        self.assertEqual(25, int(interior.sum()))
        self.assertTrue(interior[3:8, 3:8].all())

    def test_front_normalization_preserves_side_brightness_mismatch(self):
        native = np.full((8, 8, 3), 80., dtype=float)
        product = np.full_like(native, 100.)
        front = np.zeros((8, 8), dtype=bool)
        front[:4, :] = True
        side = ~front
        native[side] = 32.
        product[side] = 40.
        matching = appearance(product, native, front, side)
        self.assertAlmostEqual(1., matching['relative_side_over_front_gain_p10_p50_p90'][1])
        product[side] = 100.
        changed = appearance(product, native, front, side)
        self.assertAlmostEqual(2.5, changed['relative_side_over_front_gain_p10_p50_p90'][1])
        self.assertFalse(appearance(product, native, front, np.zeros_like(side))['measurable'])

    def test_depth_raster_retains_texel_identity_and_serializable_side_samples(self):
        texture = Image.new('RGBA', (2, 1))
        texture.putdata(((220, 40, 30, 255), (30, 180, 60, 255)))
        pose = {'size_pixels': 16., 'front_z_pixels': 14.75, 'thickness_pixels': 2.}
        row = {'state': {'origin': (0., 0., 0.)}, 'camera_expected': {
            'position': (2.5, 1.5, 2.5), 'target': (.5, .5, .5)}}
        owners, surfaces = side_surfaces((0., 0., 0.), texture, pose, 2, 0., row,
                                          (256, 256), {'vertical_fov': 35.})
        self.assertEqual(10, len(surfaces))
        self.assertFalse(any(surface['kind'] == 'side' and
            (surface['texel'] == [0, 0] and surface['edge'] == 'right' or
             surface['texel'] == [1, 0] and surface['edge'] == 'left')
            for surface in surfaces))
        visible = {surfaces[int(index)]['kind'] for index in np.unique(owners) if index >= 0}
        self.assertEqual({'back', 'side'}, visible)
        product = np.zeros((256, 256, 3))
        native = np.zeros_like(product)
        for index, surface in enumerate(surfaces):
            self.assertEqual(list(texture.getpixel(tuple(surface['texel'])))[:3], surface['color'])
            product[owners == index] = np.array(surface['color']) * .7
            native[owners == index] = np.array(surface['color']) * .5
        measurements = surface_appearance(product, native, owners >= 0, owners, surfaces)
        self.assertTrue(measurements)
        self.assertEqual(measurements, json.loads(json.dumps(measurements)))
        for surface in measurements:
            self.assertAlmostEqual(1., np.linalg.norm(surface['normal']))
            self.assertAlmostEqual(.7, surface['product_source_luma_gain'])
            self.assertAlmostEqual(.5, surface['native_source_luma_gain'])
            self.assertAlmostEqual(0., surface['product_native_chroma_error_p95'])
        swapped = product[:, :, ::-1]
        wrong = surface_appearance(swapped, native, owners >= 0, owners, surfaces)
        self.assertGreater(max(surface['product_source_chroma_error_p95'] for surface in wrong), .05)


if __name__ == '__main__':
    unittest.main()
