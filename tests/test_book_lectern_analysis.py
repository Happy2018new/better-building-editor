"""Native close-up comparison must reject dark, absent or displaced pages."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_lectern_book_r17 import compare


class LecternPageAnalysisTests(unittest.TestCase):
    def test_page_parity_rejects_missing_dark_and_displaced_surfaces(self):
        reference = np.full((180, 240, 3), (143., 188., 253.))
        reference[30:130, 40:180] = (211., 200., 157.)
        self.assertTrue(compare(reference, reference)['passed'])
        missing = np.full_like(reference, (143., 188., 253.))
        self.assertFalse(compare(reference, missing)['passed'])
        dark = reference.copy()
        dark[30:130, 40:180] *= .7
        self.assertFalse(compare(reference, dark)['passed'])
        displaced = np.roll(reference, 15, axis=0)
        self.assertFalse(compare(reference, displaced)['passed'])
