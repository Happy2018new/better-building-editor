"""Coordinate controls require actual stable normals and known depth bytes."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from analyze_portal_coordinates_r20 import compare, decode


class PortalCoordinateTests(unittest.TestCase):
    @staticmethod
    def control(phase=0):
        height, width = 128, 256
        y, x = np.indices((height, width))
        depth = (x//4) % 32
        normals = (((height-1-y)//4) % 2) == 0
        present = (depth % 2) == 0
        result = np.zeros((height, width, 3), dtype=np.uint8)
        result[normals & present] = (127, 127, 0)
        uv = present & ~normals
        result[:, :, 0][uv] = x[uv] % 256
        result[:, :, 1][uv] = (y[uv]+phase) % 256
        result[:, :, 2][uv] = np.floor((depth[uv]//2)*255./16.).astype(np.uint8)
        return result

    @staticmethod
    def camera():
        return {'face_points': [('north', [
            {'screenX': x, 'screenY': y, 'isInScreen': True}
            for x, y in ((0, 0), (255, 0), (255, 127), (0, 127))])]}

    def decode_values(self, values, directory, name):
        path = Path(directory)/name
        Image.fromarray(values).save(path)
        return decode(path, self.camera())

    def test_native_color_bytes_and_uv_are_read_in_gl_fragment_row_order(self):
        with tempfile.TemporaryDirectory() as directory:
            result, _ = self.decode_values(self.control(), directory, 'normal.png')
        self.assertTrue(result['control_observed'])
        self.assertEqual([127., 127., 0.], result['layers'][0]['normal_bytes'])
        self.assertEqual([0, 15, 31, 47, 63, 79, 95, 111, 127, 143, 159, 175, 191, 207, 223, 239],
                         [row['depth_byte'] for row in result['layers']])

    def test_animation_phase_does_not_hide_texel_x_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            _, first = self.decode_values(self.control(), directory, 'first.png')
            _, second = self.decode_values(self.control(9), directory, 'second.png')
            rows = compare(first, second)
            shifted = self.control(9)
            shifted[:, :, 0] = (shifted[:, :, 0].astype(int)+3) % 256
            _, third = self.decode_values(shifted, directory, 'shifted.png')
            mismatch = compare(first, third)
        self.assertTrue(all(row['texel_x_exact_ratio'] == 1. for row in rows))
        self.assertTrue(all(row['texel_y_fitted_phase'] == 9 for row in rows))
        self.assertTrue(all(row['texel_y_phase_within_one_ratio'] == 1. for row in rows))
        self.assertTrue(all(row['texel_x_within_one_ratio'] == 0. for row in mismatch))

    def test_random_stars_and_solid_colors_cannot_establish_control(self):
        rng = np.random.default_rng(20)
        with tempfile.TemporaryDirectory() as directory:
            for name, values in (('noise.png', rng.integers(0, 256, (128, 256, 3), dtype=np.uint8)),
                                 ('solid.png', np.full((128, 256, 3), 191, dtype=np.uint8))):
                result, _ = self.decode_values(values, directory, name)
                self.assertFalse(result['control_observed'])


if __name__ == '__main__':
    unittest.main()
