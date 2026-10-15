"""Shadow controls distinguish support darkening from moving scenery."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_shelf_body_r18 import shadow_pixels


class ShelfShadowAnalysisTests(unittest.TestCase):
    def test_support_shadow_is_detected_without_counting_scenery(self):
        disabled = np.full((80, 80, 3), (60, 150, 210), dtype=np.uint8)
        disabled[20:60, 20:60] = (20, 140, 160)
        enabled = disabled.copy()
        enabled[30:45, 30:45] = (3, 100, 120)
        enabled[:10, :10] = 0
        result = shadow_pixels(enabled, disabled)
        self.assertEqual(36*36, result['support_interior_pixels'])
        self.assertEqual(15*15, result['shadow_darkened_pixels'])
        self.assertEqual(40, result['maximum_channel_change'])

    def test_unchanged_support_is_a_valid_negative_control(self):
        picture = np.full((40, 40, 3), (20, 140, 160), dtype=np.uint8)
        self.assertEqual(0, shadow_pixels(picture, picture)['shadow_darkened_pixels'])


if __name__ == '__main__':
    unittest.main()
