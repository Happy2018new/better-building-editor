"""Flow direction gates must reject reverse motion and static backgrounds."""
import sys
from pathlib import Path
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_product_water_flow import controlled_motion, motion, physical_points


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

    def test_direction_survives_repeated_frames_and_independent_texture_updates(self):
        # Each independent artwork translates once, is presented twice, and is
        # then replaced. Replacement and repeated frames cannot establish a
        # direction, but the eight actual translations must still be measured.
        rng = np.random.default_rng(21)
        textures = rng.normal(128, 30, (8, 96, 96))
        background = rng.normal(128, 50, (96, 96))
        times = np.arange(32) * 250000
        for axis, sign in ((1, 1), (0, 1), (1, -1), (0, -1)):
            with self.subTest(axis=axis, sign=sign):
                signal = np.array([frame + background for texture in textures
                                   for frame in (texture, texture,
                                       np.roll(texture, sign * 4, axis=axis),
                                       np.roll(texture, sign * 4, axis=axis))])
                result = motion(signal, times, axis, sign, .00884, 16)
                self.assertTrue(result['passed'])
                self.assertGreaterEqual(result['measurable_pairs'], 7)
                self.assertLess(result['correct_pair_fraction'], .7)
                self.assertGreaterEqual(result['correct_measurable_pair_fraction'], .7)
                self.assertFalse(motion(signal[::-1], times, axis, sign, .00884, 16)['passed'])
                checked = controlled_motion(signal, times, axis, sign, .00884, 16)
                self.assertTrue(checked['passed'])
                self.assertTrue(checked['reversed_time_rejected'])

    def test_mixed_direction_and_too_few_independent_moves_are_rejected(self):
        rng = np.random.default_rng(35)
        textures = rng.normal(128, 30, (8, 96, 96))
        mixed = np.array([frame for index, texture in enumerate(textures)
                          for frame in (texture, texture,
                              np.roll(texture, 4 if index % 2 else -4, axis=0),
                              np.roll(texture, 4 if index % 2 else -4, axis=0))])
        sparse = np.array([frame for texture in textures[:6]
                           for frame in (texture, texture, np.roll(texture, 4, axis=0),
                                         np.roll(texture, 4, axis=0))])
        flicker = rng.normal(128, 30, (32, 96, 96))
        for signal in (mixed, sparse, flicker):
            self.assertFalse(motion(signal, np.arange(len(signal)) * 250000,
                                    0, 1, .00884, 16)['passed'])

    def test_motion_concentrated_in_one_short_interval_is_rejected(self):
        texture = np.random.default_rng(14).normal(128, 30, (96, 96))
        # Eight unambiguous moves cannot qualify the rest of a static burst.
        signal = np.array([np.roll(texture, min(index, 8), axis=1)
                           for index in range(40)])
        observed = motion(signal, np.arange(40) * 250000, 1, 1, .00884, 16)
        self.assertGreaterEqual(observed['measurable_pairs'], 7)
        self.assertGreaterEqual(observed['correct_measurable_pair_fraction'], .7)
        self.assertFalse(observed['passed'])
        self.assertLess(observed['measurable_span_fraction'], .6)


if __name__ == '__main__':
    unittest.main()
