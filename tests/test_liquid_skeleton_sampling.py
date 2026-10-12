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

    def test_no_blend_keeps_first_frame_at_half_tick(self):
        image = Image.new('RGBA', (16, 32), (16, 32, 48, 255))
        image.paste((224, 192, 160, 255), (0, 16, 16, 32))
        def expected(blend):
            return next(row['expected'] for row in fixtures(image, 1, False, blend=blend)
                        if row['name'] == '0.125/0.125/0.5/-1.0')
        self.assertEqual([1, 7, 16, 128], expected(False))
        self.assertNotEqual(expected(False), expected(True))

    def test_partial_side_height_reads_lower_source_rows_in_all_four_directions(self):
        image = Image.new('RGBA', (16, 32), (255, 255, 255, 255))
        for y in range(16):
            for x in range(16):
                image.putpixel((x, y), (16 * y, 16 * y, 16 * y, 255))
        rows = [row for row in fixtures(image, 1, True) if row['name'].startswith('lower_crop/')]
        self.assertEqual(16, len(rows))
        self.assertEqual({1, 2, 3, 4}, {int(row['name'].split('/')[1]) for row in rows})
        north = next(row for row in rows if row['name'] == 'lower_crop/1/0.625/1.0')
        self.assertGreater(north['expected'][0], 0)
        self.assertLess(north['expected'][0], 18)


if __name__ == '__main__':
    unittest.main()
