import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_native_plant_anchors import root_measurement, saved_frame, solve_offsets, summarize
from verify_snow_plant_visibility import green_mask


class NativePlantAnchorTests(unittest.TestCase):
    def test_two_orthogonal_roots_recover_offsets_without_full_leaf_masks(self):
        focal, x, z = 360., .08, -.06
        rows = [
            {'target': (6, 8, 6), 'view': 'front', 'roots_valid': True,
             'root_delta_pixels': [-focal*x/(3.-z), .2], 'focal_pixels': focal},
            {'target': (6, 8, 6), 'view': 'right', 'roots_valid': True,
             'root_delta_pixels': [focal*z/(3.-x), -.3], 'focal_pixels': focal},
        ]
        result = solve_offsets(rows)
        self.assertEqual(1, len(result))
        self.assertAlmostEqual(x, result[0]['offset_blocks'][0])
        self.assertAlmostEqual(z, result[0]['offset_blocks'][2])
        self.assertEqual(.3, result[0]['root_vertical_error_pixels'])
        rows[1]['roots_valid'] = False
        self.assertEqual([], solve_offsets(rows))

    def test_root_strip_excludes_upper_leaves_and_support_pixels(self):
        image = Image.new('RGB', (100, 100))
        draw = ImageDraw.Draw(image)
        draw.rectangle((48, 48, 52, 52), fill=(35, 155, 45))
        draw.rectangle((30, 10, 69, 35), fill=(35, 155, 45))
        draw.rectangle((40, 53, 60, 69), fill=(35, 155, 45))
        mask, measured = root_measurement({'image': image, 'green': green_mask(image)}, 100.)
        self.assertEqual((48, 48, 53, 53), mask.getbbox())
        self.assertEqual(25, measured['pixels'])
        self.assertEqual([50., 50.], measured['centroid'])

    def test_offset_camera_keeps_crosshair_outside_measurement_and_preserves_solution(self):
        focal, x, z, width = 360., -.11, .07, 866.
        baseline_u, baseline_v = -.5/3., -.5/3.
        native_u, native_v = (-.5+x)/(3.-z), (-.5+z)/(3.-x)
        rows = [
            {'target': (6, 8, 6), 'view': 'front', 'roots_valid': True,
             'root_delta_pixels': [-focal*(native_u-baseline_u), 0.],
             'focal_pixels': focal, 'screenshot_width': width,
             'projection_root': {'centroid': [width/2.-focal*baseline_u, 240.]}},
            {'target': (6, 8, 6), 'view': 'right', 'roots_valid': True,
             'root_delta_pixels': [focal*(native_v-baseline_v), 0.],
             'focal_pixels': focal, 'screenshot_width': width,
             'projection_root': {'centroid': [width/2.+focal*baseline_v, 240.]}},
        ]
        solved = solve_offsets(rows)[0]['offset_blocks']
        self.assertAlmostEqual(x, solved[0])
        self.assertAlmostEqual(z, solved[2])

    def test_horizontal_clipping_rejects_incomplete_root_measurement(self):
        image = Image.new('RGB', (100, 100))
        ImageDraw.Draw(image).rectangle((0, 48, 25, 52), fill=(35, 155, 45))
        _, measured = root_measurement({'image': image, 'green': green_mask(image)}, 100.)
        self.assertTrue(measured['horizontal_clipping'])

    def test_replay_rejects_changed_saved_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'changed.png'
            Image.new('RGB', (10, 10)).save(path)
            capture = {'path': str(path), 'sha256': '0'*64, 'size': (10, 10)}
            with self.assertRaisesRegex(AssertionError, 'Saved root capture changed'):
                saved_frame({'shown': capture, 'hidden': capture})

    def test_valid_root_evidence_does_not_accept_failed_foliage(self):
        row = {'roots_valid': True, 'absolute_snow_comparison': {'passed': True},
               'raw_foliage_comparison': {'passed': False}, 'focal_pixels': 360.,
               'root_delta_pixels': (0., 0.)}
        report = {'rows': [dict(row, target=target, view=view) for target in
                           ((6, -52, 6), (7, -52, 6), (6, -52, 7)) for view in ('front', 'right')]}
        summarize(report)
        self.assertTrue(report['valid'])
        self.assertTrue(report['all_snow_anchors_passed'])
        self.assertFalse(report['raw_foliage_accepted'])


if __name__ == '__main__':
    unittest.main()
