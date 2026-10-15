"""Reject the double logical-screen scaling found in the 3.10 snow suite."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from snow_native_projection_r20 import physical_roi


class SnowNativeProjectionR20Tests(unittest.TestCase):
    def setUp(self):
        self.points = [{'screenX': x, 'screenY': y, 'isInScreen': True}
                       for x, y in ((850, 450), (850, 650), (900, 400), (900, 700),
                                    (1100, 450), (1100, 650), (1050, 400), (1050, 700))]

    def test_physical_corners_remain_in_the_actual_capture_cell(self):
        mask, polygon = physical_roi(self.points, (1994, 1105), (498, 276, 1495, 828))
        self.assertEqual((352, 124, 603, 425), mask.getbbox())
        self.assertEqual(8, len(polygon))

    def test_old_double_scaling_and_logical_coordinate_crops_are_rejected(self):
        scaled = [dict(row, screenX=row['screenX'] * 4, screenY=row['screenY'] * 4) for row in self.points]
        with self.assertRaisesRegex(ValueError, 'physical pixels'):
            physical_roi(scaled, (1994, 1105), (498, 276, 1495, 828))
        logical = [dict(row, screenX=row['screenX'] / 4, screenY=row['screenY'] / 4) for row in self.points]
        with self.assertRaisesRegex(ValueError, 'empty or too small'):
            physical_roi(logical, (1994, 1105), (498, 276, 1495, 828))

    def test_incomplete_offscreen_or_nonfinite_native_controls_are_rejected(self):
        for bad in (self.points[:-1], [dict(row, isInScreen=False) for row in self.points],
                    [dict(row, screenX=float('nan')) for row in self.points]):
            with self.subTest(points=bad), self.assertRaises(ValueError):
                physical_roi(bad, (1994, 1105), (498, 276, 1495, 828))


if __name__ == '__main__':
    unittest.main()
