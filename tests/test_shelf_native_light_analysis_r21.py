import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_shelf_native_light_r21 import sample_stripes


class NativeShelfStripesTests(unittest.TestCase):
    def fixture(self, origin):
        colors = np.array(((255, 0, 255), (210, 210, 210),
                           (237, 237, 237), (255, 73, 0)), dtype=np.uint8)
        return np.tile(colors[((origin + np.arange(380)) // 16) % 4], (300, 1, 1))

    def test_physical_phase_and_independent_light_values(self):
        result = sample_stripes(self.fixture(247), 247)
        self.assertTrue(result['readback_valid'])
        self.assertEqual(result['stripes'][1]['min_rgb'], [210, 210, 210])
        self.assertEqual(result['stripes'][2]['min_rgb'], [237, 237, 237])
        self.assertEqual(sum(row['pixels'] for row in result['stripes']), 2000)

    def test_crop_relative_phase_is_rejected(self):
        self.assertFalse(sample_stripes(self.fixture(247), 0)['readback_valid'])

    def test_textured_or_corrupt_selector_is_rejected(self):
        picture = self.fixture(247)
        picture[160:180, 140:240] = (126, 92, 44)
        self.assertFalse(sample_stripes(picture, 247)['readback_valid'])

    def test_invalid_flag_encoding_is_rejected(self):
        picture = self.fixture(0)
        for x in range(140, 240):
            if (x // 16) % 4 == 3:
                picture[160:180, x] = (255, 17, 255)
        self.assertFalse(sample_stripes(picture, 0)['readback_valid'])


if __name__ == '__main__':
    unittest.main()
