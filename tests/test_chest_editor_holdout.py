"""Independent registration cannot absorb chest-specific offsets or scaling."""
import sys
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_chest_editor_frozen_holdout import compare, registration


class ChestEditorHoldoutTests(unittest.TestCase):
    def setUp(self):
        self.transform = registration({'world_bounds': [0, 0, 100, 100]},
                                      {'world_bounds': [200, 100, 400, 300]})
        image = Image.new('RGB', (64, 64))
        image.putdata([(40 + (x*17+y*23) % 160, 90, 50)
                       for y in range(64) for x in range(64)])
        self.image = image
        self.mask = Image.new('L', (64, 64), 255)

    def row(self, bounds):
        return self.image, self.mask, {'bbox': bounds, 'world_bounds': bounds}

    def test_independent_cube_accepts_matching_registered_chest(self):
        result = compare(self.row([10, 10, 90, 90]), self.row([220, 120, 380, 280]), self.transform)
        self.assertTrue(result['passed'], result)

    def test_chest_offset_cannot_recalibrate_registration(self):
        result = compare(self.row([10, 10, 90, 90]), self.row([226, 120, 386, 280]), self.transform)
        self.assertFalse(result['passed'])
        self.assertEqual(6., result['alignment']['center_distance_pixels'])
        self.assertEqual(2., self.transform['scale'])

    def test_anisotropic_cube_registration_is_rejected(self):
        with self.assertRaises(AssertionError):
            registration({'world_bounds': [0, 0, 100, 100]}, {'world_bounds': [0, 0, 110, 150]})


if __name__ == '__main__':
    unittest.main()
