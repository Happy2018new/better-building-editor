"""Independent submerged/rear controls reject opaque water and omitted water."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_liquid_transparency import alpha_row, contrast_row, contribution_row, pixel_regions
from probe_liquid_workspace import scene_transparency_regions


class LiquidTransparencyControlsTests(unittest.TestCase):
    def controls(self):
        empty = np.full((100, 100, 3), 230, dtype=np.int16)
        no_water, liquid = empty.copy(), empty.copy()
        regions = {'submerged_body': (5, 60, 25, 85), 'behind_block': (65, 60, 85, 85)}
        for x0, y0, x1, y1 in regions.values():
            no_water[y0:y1, x0:x1] = (120, 80, 20)
            liquid[y0:y1, x0:x1] = (40, 90, 170)
        positive = liquid + np.rint((no_water - empty) * .35).astype(np.int16)
        return positive, no_water, liquid, empty, regions

    def test_both_bodies_and_water_must_contribute_beneath_water(self):
        controls = self.controls()
        result = contribution_row(*controls)
        self.assertEqual('OBSERVED', result['status'])
        self.assertFalse(result['native_alpha_accepted'])
        for name,row in result['regions'].items():
            self.assertEqual(500 if name=='submerged_body' else 450, row['eligible_pixels'])
            self.assertAlmostEqual(.35, row['median_body_transmission'], places=2)

    def test_opaque_water_and_absent_water_are_rejected(self):
        positive, no_water, liquid, empty, regions = self.controls()
        for invalid in (liquid, no_water):
            result = contribution_row(invalid, no_water, liquid, empty, regions)
            self.assertEqual('FAIL', result['status'])

    def test_a_visible_cap_or_only_one_visible_body_cannot_pass(self):
        positive, no_water, liquid, empty, regions = self.controls()
        positive[10:30, 5:25] = no_water[10:30, 5:25]
        positive[60:85, 5:25] = liquid[60:85, 5:25]
        result = contribution_row(positive, no_water, liquid, empty, regions)
        self.assertEqual('FAIL', result['status'])
        self.assertEqual('OBSERVED', result['regions']['behind_block']['status'])

    def test_regions_are_inset_from_geometry_and_reject_invalid_dimensions(self):
        regions = {'submerged_body': [[10.1, 20.2], [15.9, 30.8]]}
        self.assertEqual([21, 41, 31, 61], pixel_regions(regions, (100, 100), (200, 200))['submerged_body'])
        with self.assertRaises(ValueError):
            pixel_regions(regions, (10, 10), (200, 200))

    def test_front_view_regions_use_control_layout_without_image_selection(self):
        state = {'camera_pose': [0., 0., 3.], 'liquid_control_requests': [{
            'visible': [False, True], 'poses': [None, [.1, -90., 0., 0.]],
            'doll_positions': [[0., 0.], [0., 0.]], 'doll_sizes': [[200., 200.], [200., 200.]]}]}
        result = scene_transparency_regions(state)
        self.assertAlmostEqual(128.6, result['submerged_body'][0][0])
        self.assertAlmostEqual(26., result['submerged_body'][0][1])
        state['camera_pose'][0] = 15.
        with self.assertRaises(ValueError):
            scene_transparency_regions(state)

    def contrast_controls(self):
        positive, dry, opaque, unused, regions = self.controls()
        dark_dry = np.full_like(dry, 15)
        bright_wet = np.rint(dry * .55 + opaque * .45).astype(np.int16)
        dark_wet = np.rint(dark_dry * .55 + opaque * .45).astype(np.int16)
        return bright_wet, dry, dark_wet, dark_dry, regions

    def test_same_geometry_contrast_observes_both_submerged_bodies(self):
        result = contrast_row(*self.contrast_controls())
        self.assertEqual('OBSERVED', result['status'])
        for row in result['regions'].values():
            self.assertAlmostEqual(.55, row['transmission'], places=2)
            self.assertLess(row['rgb_rmse'], 1.)

    def test_same_geometry_contrast_rejects_opaque_or_omitted_water(self):
        bright_wet, bright_dry, dark_wet, dark_dry, regions = self.contrast_controls()
        for bright, dark in ((dark_wet, dark_wet), (bright_dry, dark_dry)):
            self.assertEqual('FAIL', contrast_row(bright, bright_dry, dark, dark_dry, regions)['status'])
        with self.assertRaises(ValueError):
            contrast_row(bright_wet[:-1], bright_dry, dark_wet, dark_dry, regions)

    def alpha_controls(self):
        unused, clear, opaque, unused_empty, regions = self.controls()
        images = {'0': clear, '1': opaque}
        for name, alpha in (('0_25', .25), ('0_45', .45), ('0_75', .75), ('default', .45)):
            images[name] = np.rint(clear * (1. - alpha) + opaque * alpha).astype(np.int16)
        return images, regions

    def test_fixed_water_endpoints_observe_body_and_water_at_all_opacities(self):
        result = alpha_row(*self.alpha_controls())
        self.assertEqual('OBSERVED', result['status'])
        self.assertFalse(result['native_alpha_accepted'])
        for row in result['regions'].values():
            self.assertEqual(3, len(row['phases']))
            self.assertEqual(0., row['default_rgb_rmse'])

    def test_fixed_water_endpoints_reject_unresponsive_alpha_or_one_missing_body(self):
        images, regions = self.alpha_controls()
        images['0_25'] = images['1']
        self.assertEqual('FAIL', alpha_row(images, regions)['status'])
        images, regions = self.alpha_controls()
        x0,y0,x1,y1 = regions['submerged_body']
        images['0_45'][y0:y1,x0:x1] = images['1'][y0:y1,x0:x1]
        result = alpha_row(images, regions)
        self.assertEqual('FAIL', result['regions']['submerged_body']['status'])
        self.assertEqual('OBSERVED', result['regions']['behind_block']['status'])

    def test_texture_variation_is_separate_from_flat_color_transparency(self):
        images, regions = self.alpha_controls()
        result = alpha_row(images, regions)
        self.assertTrue(all(not row['water_texture_variation_observed'] for row in result['regions'].values()))
        pattern = (np.indices(images['1'].shape[:2])[0] % 7 * 6)[..., None]
        images['1'] = images['1'] + pattern
        for name, alpha in (('0_25', .25), ('0_45', .45), ('0_75', .75), ('default', .45)):
            images[name] = np.rint(images['0'] * (1. - alpha) + images['1'] * alpha).astype(np.int16)
        result = alpha_row(images, regions)
        self.assertEqual('OBSERVED', result['status'])
        self.assertTrue(all(row['water_texture_variation_observed'] for row in result['regions'].values()))


if __name__ == '__main__':
    unittest.main()
