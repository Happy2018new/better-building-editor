"""Flow direction gates must reject reverse motion and static backgrounds."""
import sys
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_product_water_flow import motion, physical_points


class ProductWaterDirectionTest(unittest.TestCase):
    def test_four_cardinals_reject_reversed_and_still_artwork(self):
        texture = np.random.default_rng(9).normal(128, 30, (96, 96))
        background = np.random.default_rng(8).normal(128, 50, (96, 96))
        times = np.arange(20) * 500000
        for axis, sign in ((1, 1), (0, 1), (1, -1), (0, -1)):
            with self.subTest(axis=axis, sign=sign):
                forward = np.array([np.roll(texture, sign * index, axis=axis) + background
                                    for index in range(20)])
                reverse = np.array([np.roll(texture, -sign * index, axis=axis) + background
                                    for index in range(20)])
                still = np.repeat(background[None], 20, axis=0)
                self.assertTrue(motion(forward, times, axis, sign, .00884, 16)['passed'])
                self.assertFalse(motion(reverse, times, axis, sign, .00884, 16)['passed'])
                self.assertFalse(motion(still, times, axis, sign, .00884, 16)['passed'])

    def test_two_second_alias_cannot_qualify_direction(self):
        texture = np.random.default_rng(4).normal(128, 30, (96, 96))
        signal = np.array([np.roll(texture, index, axis=1) for index in range(20)])
        result = motion(signal, np.arange(20) * 20000000, 1, 1, .00884, 16)
        self.assertFalse(result['passed'])
        self.assertEqual(0, result['eligible_pairs'])

    def test_top_sampling_follows_actual_planar_diagonal(self):
        shape = {'position': (3, 3, 3), 'heights': (0, 0, 1, 0)}
        points, unused = physical_points(shape, 0)
        for x, y, z in points:
            self.assertAlmostEqual(y - 3, min(x - 3, z - 3))


if __name__ == '__main__':
    unittest.main()
