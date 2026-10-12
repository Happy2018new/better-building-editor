"""Original source quadrants remain distinct in generated model controls."""
from pathlib import Path
import sys
import unittest

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from generate_liquid_skeleton_resources import sampling_region
from verify_liquid_skeleton_resources import fixtures


class LiquidSkeletonSamplingTests(unittest.TestCase):
    def test_quad_one_reads_nw_artwork_instead_of_full_frame(self):
        image = Image.new('RGBA', (32, 64), (240, 240, 240, 255))
        for y in range(16):
            for x in range(16):
                image.putpixel((x, y), (16, 32, 64, 255))
        region = sampling_region({'quad': 1})
        rows = fixtures(image, 1, True, sampling=region)
        interior = next(row for row in rows if row['name'] == '0.875/0.875/0.0/-1.0')
        self.assertEqual([1, 7, 22, 128], interior['expected'])
        old = next(row for row in fixtures(image, 1, True)
                   if row['name'] == interior['name'])
        self.assertEqual([17, 49, 81, 128], old['expected'])
        self.assertFalse(region['native_sampling_accepted'])

    def test_other_native_atlas_quadrant_contracts_are_rejected(self):
        for value in (True, -1, 2, '1', None):
            with self.assertRaises(ValueError):
                sampling_region({'quad': value})

    def test_unchanged_full_frame_contract_is_explicit(self):
        region = sampling_region({})
        self.assertEqual('full', region['region'])
        self.assertEqual('centers', region['pixel_mapping'])
        self.assertFalse(region['native_sampling_accepted'])


if __name__ == '__main__':
    unittest.main()
