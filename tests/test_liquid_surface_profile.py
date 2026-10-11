"""Silhouette diagnostics must reject geometry errors and ambiguous bodies."""
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_liquid_surface_profile import check_remote_background, compare, predicted_mask
from projection.liquid_render_plan import LiquidSurface


CAMERA = {'position': [3.5, 3.5, -4.], 'target': [.5, .5, .5],
          'screen': [800., 600.], 'native_image_screen': [800, 600], 'vertical_fov': 60.}


def water(height, faces=63):
    return [((0, 0, 0), LiquidSurface((0, 0, 0), 0, (height,) * 4, faces, 'still_water_grey'))]


class LiquidProfileChecks(unittest.TestCase):
    def test_wrong_height_fails_fixed_silhouette_thresholds(self):
        actual = predicted_mask(water(.7), CAMERA)
        wrong = predicted_mask(water(.3), CAMERA)
        metrics = compare(actual, wrong, 3)
        self.assertLess(metrics['mask_iou'], .95)
        self.assertLess(metrics['outline_recall'], .95)

    def test_missing_faces_cannot_be_accepted_by_top_outline_alone(self):
        complete = predicted_mask(water(.7), CAMERA)
        top = predicted_mask(water(.7, 1), CAMERA)
        self.assertLess(compare(complete, top, 3)['mask_iou'], .95)

    def test_missing_contributions_are_not_silently_filled_or_tolerance_fitted(self):
        expected = Image.new('L', (200, 200))
        ImageDraw.Draw(expected).rectangle((20, 20, 180, 180), fill=255)
        actual = expected.copy()
        ImageDraw.Draw(actual).rectangle((60, 20, 120, 80), fill=0)
        metrics = compare(actual, expected, 3)
        self.assertLess(metrics['outline_recall'], .95)
        self.assertEqual(3, metrics['outline_tolerance_pixels'])

    def test_remote_background_must_be_identical_in_all_controls(self):
        plate = [[(0, -2, 0), ['minecraft:quartz_block', 0]]]
        plan = {'background_cells': plate,
                'controls': dict((name, {'cells': plate + ([[[0, 0, 0], ['minecraft:water', 0]]]
                                                          if name in ('liquid_only', 'supported_positive') else [])})
                                 for name in ('empty', 'liquid_only', 'supported_positive', 'supported_negative'))}
        self.assertEqual({(0, -2, 0): ('minecraft:quartz_block', 0)}, check_remote_background(plan))
        plan['controls']['empty']['cells'] = []
        with self.assertRaises(ValueError):
            check_remote_background(plan)

    def test_neighbor_backdrop_and_waterlogged_body_are_not_pure_silhouettes(self):
        for cell in (['minecraft:stone', 0],
                     [['minecraft:oak_fence', 0], ['minecraft:water', 0], None]):
            plan = {'controls': dict((name, {'cells': []})
                                     for name in ('empty', 'liquid_only', 'supported_positive', 'supported_negative'))}
            plan['controls']['liquid_only']['cells'] = [[[0, 0, 0], cell]]
            with self.assertRaises(ValueError):
                check_remote_background(plan)

        plate = [[[0, -1, 0], ['minecraft:quartz_block', 0]]]
        plan = {'background_cells': plate, 'controls': dict((name, {'cells': plate})
                for name in ('empty', 'liquid_only', 'supported_positive', 'supported_negative'))}
        plan['controls']['liquid_only']['cells'] = plate + [[[0, 0, 0], ['minecraft:water', 0]]]
        with self.assertRaises(ValueError):
            check_remote_background(plan)
