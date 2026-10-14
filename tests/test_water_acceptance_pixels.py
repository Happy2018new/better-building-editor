"""Side and CPU budget gates reject plausible false-positive controls."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_water_acceptance_r16 import budget_checks, repetition, side_grid, visibility_pixels
from analyze_product_water import raster_depth


class WaterAcceptancePixelTests(unittest.TestCase):
    def setUp(self):
        generator = np.random.default_rng(341)
        self.side = generator.integers(50, 130, size=(14, 18, 3)).astype(float)

    def test_same_side_and_small_raster_noise_are_accepted(self):
        self.assertTrue(repetition(self.side, self.side)['passed'])
        self.assertTrue(repetition(self.side, self.side + 1.5)['passed'])

    def test_mirror_and_wrong_texture_phase_are_rejected(self):
        self.assertFalse(repetition(self.side, self.side[:, ::-1])['passed'])
        self.assertFalse(repetition(self.side, np.roll(self.side, 5, axis=1))['passed'])

    def test_blank_and_low_contrast_are_rejected(self):
        self.assertFalse(repetition(self.side, np.full_like(self.side, 90.))['passed'])
        self.assertFalse(repetition(self.side / 100., self.side / 100.)['passed'])

    def test_physical_side_sampling_rejects_clipped_or_nonfinite_viewports(self):
        image = np.zeros((100, 100, 3))
        shape = {'position': (3, 3, 4), 'heights': (1.,) * 4}
        for point in ((20., 20.), (-1., 20.), (20., 100.), (float('nan'), 20.)):
            mapped = [point] * (18 * 14)
            with self.subTest(point=point), patch('analyze_water_acceptance_r16.project', return_value=mapped):
                if point == (20., 20.):
                    self.assertEqual((14, 18), side_grid(image, shape, 2, {}, {})[0])
                else:
                    with self.assertRaisesRegex(ValueError, 'leave the native viewport'):
                        side_grid(image, shape, 2, {}, {})

    def test_cpu_budget_rejects_spikes_and_missing_measurement(self):
        passing = budget_checks({'owner_timing_ms': {'advance': [1.] * 100}})['advance']
        self.assertTrue(passing['passed'])
        for values in ([1.] * 10, [1.] * 99 + [101.], [20.] * 100,
                       [float('nan')] * 100, [-1.] * 100):
            with self.subTest(values=values[-1]):
                self.assertFalse(budget_checks({'owner_timing_ms': {'advance': values}})['advance']['passed'])

    def test_hidden_native_body_cannot_substitute_for_visible_water(self):
        dry = np.full((14, 18, 3), 100, dtype=np.uint8)
        hidden = np.full_like(dry, 240)
        mask = np.ones(dry.shape[:2], dtype=bool)
        invisible = visibility_pixels(dry, dry, hidden, dry, mask)
        self.assertEqual(0, invisible['independently_visible_water_pixels'])
        self.assertEqual(0, invisible['visible_water_pixels_removed'])
        self.assertIsNone(invisible['restored_rgb_rmse'])
        wet = dry.copy()
        wet[2:10, 3:15] = 130
        visible = visibility_pixels(wet, dry, hidden, wet, mask)
        self.assertEqual(96, visible['independently_visible_water_pixels'])
        self.assertEqual(96, visible['visible_water_pixels_removed'])
        self.assertEqual(0., visible['restored_rgb_rmse'])

    def test_depth_oracle_preserves_near_surface_in_either_submission_order(self):
        points = ((2., 2.), (8., 2.), (8., 8.), (2., 8.))
        for depths in ((3., 9.), (9., 3.)):
            buffer = np.full((10, 10), np.inf)
            for depth in depths:
                raster_depth(buffer, points, [depth] * 4, False)
            np.testing.assert_allclose(buffer[2:8, 2:8], 3., atol=1e-12, rtol=0.)
            self.assertFalse(np.isfinite(buffer[:2]).any())

    def test_depth_oracle_uses_perspective_correct_interpolation(self):
        points = ((1., 1.), (9., 1.), (9., 9.), (1., 9.))
        affine = np.full((10, 10), np.inf)
        perspective = affine.copy()
        raster_depth(affine, points, [2., 4., 4., 2.], False)
        raster_depth(perspective, points, [2., 4., 4., 2.], True)
        self.assertTrue(np.all(perspective[1:9, 1:9] <= affine[1:9, 1:9]))
        self.assertGreater(affine[4, 4], perspective[4, 4])


if __name__ == '__main__':
    unittest.main()
