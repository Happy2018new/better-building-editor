"""Cover raster corruption must be detected without flagging texture edges."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
from analyze_book_surface_r17 import artwork_distribution, isolated_cover_pixels, MAX_ISOLATED_PIXELS


class BookSurfaceAnalysisTests(unittest.TestCase):
    def test_artwork_detects_inside_face_without_confusing_exposure(self):
        outside = np.full((100, 100, 3), (129., 86., 37.))
        outside[:20] = (78., 51., 22.)
        inside = np.full((100, 100, 3), (78., 51., 22.))
        inside[:40] = (129., 86., 37.)
        self.assertAlmostEqual(.2, artwork_distribution(outside))
        self.assertAlmostEqual(.2, artwork_distribution(outside*.8))
        self.assertAlmostEqual(.6, artwork_distribution(inside))

    def test_narrow_cover_does_not_grant_artwork_acceptance(self):
        image = np.full((60, 80, 3), (129., 86., 37.))
        self.assertIsNone(artwork_distribution(image))

    def test_uniform_and_artwork_regions_do_not_report_speckles(self):
        image = np.full((60, 80, 3), (77, 51, 22), dtype=np.int16)
        image[10:40, 15:60] = (106, 71, 30)
        self.assertEqual(0, isolated_cover_pixels(image).sum())

    def test_isolated_corrupted_fragments_exceed_noise_limit(self):
        image = np.full((60, 80, 3), (77, 51, 22), dtype=np.int16)
        image[5:55:5, 5:75:5] = (106, 71, 30)
        self.assertGreater(isolated_cover_pixels(image).sum(), MAX_ISOLATED_PIXELS)

    def test_foliage_and_crosshair_are_not_book_cover_corruption(self):
        image = np.full((60, 80, 3), (18, 65, 12), dtype=np.int16)
        image[5:55:5, 5:75:5] = (77, 51, 22)
        image[25:30, 20:50] = (200, 220, 240)
        self.assertEqual(0, isolated_cover_pixels(image).sum())
