"""Synthetic masks verify visible-corner extraction, not native water rules."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from find_liquid_surface_corners import find_candidates, visible_corners
from measure_native_liquid_surface import CORNERS, pixel_viewport, projected_pixels
from verify_missing_neighbor_visuals import hull

CAMERA = {'position': (-5., 4., -7.), 'target': (.5, .5, .5),
          'screen': (499, 277), 'native_image_screen': (1994, 1105), 'vertical_fov': 66.6}


def synthetic_mask(camera, heights):
    mask = Image.new('L', tuple(camera['native_image_screen']))
    points = [(x, height, z) for (x, z), height in zip(CORNERS, heights)]
    points += [(x, 0., z) for x, z in CORNERS]
    projected = projected_pixels(points, camera, pixel_viewport(camera))
    ImageDraw.Draw(mask).polygon(hull((row['screenX'], row['screenY']) for row in projected), fill=255)
    return mask


class LiquidSurfaceCandidateTests(unittest.TestCase):
    def test_opposite_diagonals_cover_all_corners_without_filling_interior_junctions(self):
        heights, observed = (.4, .5, .6, .5), set()
        for position in ((-5., 4., -7.), (6., 4., 8.)):
            camera = dict(CAMERA, position=position)
            result = find_candidates(synthetic_mask(camera, heights), camera, (0, 0, 0))
            candidates = [row for row in result['corners'] if row['status'] == 'candidate']
            self.assertEqual(3, len(candidates))
            for row in candidates:
                observed.add(row['corner'])
                lower, upper = row['diagnostic']['height_interval']
                self.assertLessEqual(lower, heights[CORNERS.index(row['corner'])])
                self.assertGreaterEqual(upper, heights[CORNERS.index(row['corner'])])
            interior = [row for row in result['corners'] if row['status'] == 'unobservable']
            self.assertEqual('near_top_corner_is_interior_junction', interior[0]['reason'])
            self.assertNotIn('diagnostic', interior[0])
            self.assertFalse(result['native_geometry_accepted'])
            self.assertFalse(result['accuracy_accepted'])
            self.assertFalse(result['public_controls_eligible'])
        self.assertEqual(set(CORNERS), observed)

    def test_empty_mask_is_unobservable(self):
        result = find_candidates(Image.new('L', CAMERA['native_image_screen']), CAMERA, (0, 0, 0))
        self.assertEqual(0, result['independent_mask_pixels'])
        self.assertTrue(all(row['status'] == 'unobservable' for row in result['corners']))

    def test_disconnected_pixels_outside_fixed_cell_cannot_move_hull(self):
        original = synthetic_mask(CAMERA, (.6,) * 4)
        changed = original.copy()
        ImageDraw.Draw(changed).rectangle((10, 10, 200, 200), fill=255)
        self.assertEqual(find_candidates(original, CAMERA, (0, 0, 0)),
                         find_candidates(changed, CAMERA, (0, 0, 0)))

    def test_nonbinary_or_cropped_masks_are_rejected(self):
        for image in (Image.new('L', CAMERA['native_image_screen'], 100),
                      Image.new('RGB', CAMERA['native_image_screen']), Image.new('L', (100, 100))):
            with self.subTest(mode=image.mode, size=image.size), self.assertRaises(ValueError):
                find_candidates(image, CAMERA, (0, 0, 0))

    def test_camera_inside_lateral_footprint_or_below_top_is_rejected(self):
        for position in ((.5, 4., -7.), (-5., 4., .5), (-5., .9, -7.)):
            with self.subTest(position=position), self.assertRaises(ValueError):
                visible_corners(dict(CAMERA, position=position), (0, 0, 0))

    def test_invalid_budget_and_pixel_minimum_are_rejected(self):
        mask = synthetic_mask(CAMERA, (.6,) * 4)
        for budget, minimum in ((-1., 100), (float('nan'), 100), (3., 0)):
            with self.subTest(budget=budget, minimum=minimum), self.assertRaises(ValueError):
                find_candidates(mask, deepcopy(CAMERA), (0, 0, 0), budget, minimum)
