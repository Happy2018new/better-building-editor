"""Unchanged tints and tiny pixel noise must not qualify biome rendering."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_product_water_biome import color_change


class WaterBiomePixelGateTest(unittest.TestCase):
    def setUp(self):
        self.image = np.full((10, 10, 3), 80, dtype=np.uint8)
        self.region = np.ones((10, 10), dtype=bool)

    def test_same_color_rejected(self):
        self.assertFalse(color_change(self.image, self.image.copy(), self.region)['passed'])

    def test_small_noise_rejected(self):
        noisy = self.image + 2
        self.assertFalse(color_change(self.image, noisy, self.region)['passed'])

    def test_visible_region_change_accepted(self):
        changed = self.image.copy()
        changed[:, :7, 0] += 12
        self.assertTrue(color_change(self.image, changed, self.region)['passed'])

    def test_change_outside_selected_region_rejected(self):
        changed = self.image.copy()
        changed[:2, :, 0] += 40
        self.region[:2] = False
        self.assertFalse(color_change(self.image, changed, self.region)['passed'])


if __name__ == '__main__':
    unittest.main()
