import sys
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_portal_reference_appearance_r20 import absolute_statistics, surface_values


class AbsolutePortalAppearanceTest(unittest.TestCase):
    def test_brightness_and_density_are_not_normalized(self):
        values = np.zeros((1000, 3), dtype=np.uint8)
        values[:200] = (2, 30, 40)
        original = absolute_statistics(values)
        brighter = absolute_statistics(values*2)
        denser = values.copy()
        denser[200:400] = (2, 30, 40)
        more_stars = absolute_statistics(denser)
        self.assertAlmostEqual(brighter['luminance_mean'], original['luminance_mean']*2.)
        self.assertAlmostEqual(brighter['cyan_star_ratio'], original['cyan_star_ratio'])
        self.assertAlmostEqual(more_stars['cyan_star_ratio'], original['cyan_star_ratio']*2.)

    def test_particle_contamination_stays_in_raw_statistics(self):
        values = np.zeros((100, 3), dtype=np.uint8)
        values[0] = (200, 0, 200)
        measured = absolute_statistics(values)
        self.assertEqual(measured['magenta_contamination_pixels'], 1)
        self.assertGreater(measured['luminance_mean'], 0.)
        self.assertEqual(measured['excluded_pixels'], 0)

    def test_bright_exterior_cannot_replace_finite_face(self):
        image = Image.new('RGB', (100, 100), 'white')
        image.paste((0, 0, 0), (20, 20, 80, 80))
        camera = {'face_points': [('north', [dict(screenX=x, screenY=y, isInScreen=True)
                                            for x, y in ((30, 30), (70, 30), (70, 70), (30, 70))])]}
        measured = absolute_statistics(surface_values(image, camera, 'north'))
        self.assertEqual(measured['luminance_mean'], 0.)
        self.assertEqual(measured['cyan_star_pixels'], 0)


if __name__ == '__main__':
    unittest.main()
