"""Keep inverse-color crosshairs and corrupt marker cells out of route evidence."""
import hashlib
import math
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from probe_native_frame_matrix import BIAS, CONTROLS, SCALE, decode
from probe_native_frame_route import marker_pixels
import probe_native_frame_route as route


def capture_record(path, image):
    image.save(path)
    payload = path.read_bytes()
    row = {'path': str(path), 'sha256': hashlib.sha256(payload).hexdigest(),
           'bytes': len(payload), 'size': image.size, 'mime': 'image/png'}
    row['capture'] = dict(row, width=image.width, height=image.height,
                          frame={'width': image.width, 'height': image.height})
    return row


class NativeFrameMarkers(unittest.TestCase):
    def test_binding_failure_does_not_claim_fixture_mutation_or_restoration(self):
        with TemporaryDirectory() as directory:
            output = Path(directory) / 'failed.json'
            saved = {}
            with patch.object(sys, 'argv', ['probe_native_frame_route.py', str(output)]), \
                    patch.dict(route.os.environ, {'MCDEV_NATIVE_CAPTURE_HELPER': str(ROOT / 'tools/capture_native_window.py')}), \
                    patch.object(route, 'freeze_sources', return_value=[]), \
                    patch.object(route, 'write_json', side_effect=lambda path, report: saved.update(report)), \
                    patch.object(route, 'Client') as client, \
                    patch.object(route, 'SignCheck') as check:
                client.return_value.__enter__.side_effect = RuntimeError('binding returned no value')
                self.assertEqual(1, route.main())
            check.assert_not_called()
            self.assertFalse(saved['binding_verified'])
            self.assertFalse(saved['mutation_attempted'])
            self.assertFalse(saved['restore_attempted'])
            self.assertFalse(saved['restoration_applicable'])
            self.assertFalse(saved['restored'])
            self.assertFalse(saved['production_rendering_accepted'])

    def test_inverse_crosshair_does_not_become_a_green_material_control(self):
        with TemporaryDirectory() as directory:
            image = Image.new('RGB', (300, 300), (255, 0, 255))
            draw = ImageDraw.Draw(image)
            draw.rectangle((148, 136, 152, 164), fill=(0, 255, 0))
            draw.rectangle((136, 148, 164, 152), fill=(0, 255, 0))
            row = capture_record(Path(directory) / 'marker.png', image)
            self.assertTrue(marker_pixels(row)['positive'])
            self.assertEqual(0, marker_pixels(row, 'green')['pixels'])

    def test_real_green_surface_outside_the_crosshair_is_a_positive_control(self):
        with TemporaryDirectory() as directory:
            image = Image.new('RGB', (300, 300), (100, 150, 220))
            ImageDraw.Draw(image).rectangle((102, 104, 116, 116), fill=(0, 255, 0))
            row = capture_record(Path(directory) / 'marker.png', image)
            self.assertTrue(marker_pixels(row, 'green')['positive'])
            self.assertEqual(0, marker_pixels(row)['pixels'])

    def test_signed24_marker_needs_both_controls_and_uniform_sample_pixels(self):
        rectangle = (0, 0, 16, 24)
        values = [float(index) - 8 for index in range(16)] + [16., .5, 1., 19487. / 8., 1., 1.] + list(CONTROLS)
        image = Image.new('RGB', (16, 24))
        draw = ImageDraw.Draw(image)
        for index, value in enumerate(values):
            code = int(math.floor(value * SCALE + .5)) + BIAS
            color = (code >> 16, code >> 8 & 255, code & 255)
            x, y = index % 4 * 4, index // 4 * 4
            draw.rectangle((x, y, x + 3, y + 3), fill=color)
        self.assertTrue(decode(image, rectangle, 'WORLDVIEW')['passed'])
        corrupted = image.copy()
        corrupted.putpixel((1, 2), (0, 0, 0))
        self.assertFalse(decode(corrupted, rectangle, 'WORLDVIEW')['passed'])
        self.assertFalse(decode(Image.new('RGB', (16, 24)), rectangle, 'WORLDVIEW')['passed'])

    def test_scattered_marker_pixels_do_not_pass_connected_area_gate(self):
        with TemporaryDirectory() as directory:
            image = Image.new('RGB', (300, 300), (100, 150, 220))
            for x in range(100, 124, 2):
                for y in range(100, 124, 2):
                    image.putpixel((x, y), (0, 255, 255))
            row = capture_record(Path(directory) / 'noise.png', image)
            scored = marker_pixels(row, 'cyan')
            self.assertGreaterEqual(scored['pixels'], 80)
            self.assertEqual(1, scored['largest_connected_pixels'])
            self.assertFalse(scored['positive'])

    def test_unchanged_background_color_cannot_count_as_actor_marker(self):
        with TemporaryDirectory() as directory:
            directory = Path(directory)
            image = Image.new('RGB', (300, 300), (0, 255, 255))
            shown = capture_record(directory / 'shown.png', image)
            hidden = capture_record(directory / 'hidden.png', image)
            self.assertFalse(marker_pixels(shown, 'cyan', hidden)['positive'])


if __name__ == '__main__':
    unittest.main()
