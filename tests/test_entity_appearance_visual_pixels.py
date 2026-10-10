"""Appearance acceptance rejects blank or reversed low-contrast textures."""
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_entity_appearance_visuals import appearance_offset, comparison, texture_comparison
from verify_shulker_orientations import opacity_comparison


class AppearancePixelTests(unittest.TestCase):
    def test_wall_camera_is_on_the_exposed_side_of_each_support(self):
        configured = (-2., -.8, -3.)
        normals = {2: (0, 0, -1), 3: (0, 0, 1), 4: (-1, 0, 0), 5: (1, 0, 0)}
        for facing, normal in normals.items():
            offset = appearance_offset({'face': facing}, configured, True)
            self.assertGreater(sum(left * right for left, right in zip(offset, normal)), 0)
            self.assertEqual(configured, appearance_offset({'face': facing}, configured, False))
        self.assertEqual(configured, appearance_offset({'face': 1}, configured, True))

    def test_blank_native_reference_cannot_accept_visible_projection(self):
        frame = Image.new('RGB', (32, 32), (90, 90, 90))
        blank = Image.new('L', frame.size, 0)
        visible = Image.new('L', frame.size, 255)
        self.assertFalse(comparison(frame, blank, frame, visible)['passed'])
        self.assertFalse(texture_comparison(frame, blank, frame, visible)['passed'])

    def test_local_texture_probe_rejects_a_wrong_face_that_passes_color_tolerance(self):
        frame = Image.new('RGB', (32, 32))
        wrong = Image.new('RGB', frame.size)
        for y in range(32):
            for x in range(32):
                value = 80 if (x // 4 + y // 4) % 2 else 120
                frame.putpixel((x, y), (value, value, value))
                wrong.putpixel((x, y), (200 - value,) * 3)
        mask = Image.new('L', frame.size, 255)
        self.assertTrue(comparison(frame, mask, wrong, mask)['passed'])
        self.assertTrue(texture_comparison(frame, mask, frame, mask)['passed'])
        self.assertFalse(texture_comparison(frame, mask, wrong, mask)['passed'])

    def test_opacity_probe_accepts_nonpurple_masks_and_rejects_an_opaque_copy(self):
        empty = Image.new('RGB', (32, 32), (200, 210, 220))
        full = Image.new('RGB', empty.size, (60, 70, 80))
        half = Image.blend(empty, full, .5)
        mask = Image.new('L', empty.size, 255)
        with TemporaryDirectory() as directory:
            paths = [Path(directory) / (name + '.png') for name in ('full', 'half', 'empty')]
            for frame, path in zip((full, half, empty), paths):
                frame.save(path)
            result = opacity_comparison(paths[0], paths[1], paths[2], (0, 0, 32, 32), mask)
            self.assertTrue(result['passed'])
            self.assertAlmostEqual(.5, result['measured_contrast_gain'])
            self.assertFalse(opacity_comparison(paths[0], paths[0], paths[2], (0, 0, 32, 32), mask)['passed'])


if __name__ == '__main__':
    unittest.main()
