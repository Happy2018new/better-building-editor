"""Portal visibility must not pass on adjacent stone or a white shader fallback."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from probe_portal_reference_r19 import portal_pixels


class PortalReferencePixelsTests(unittest.TestCase):
    def measure(self, color, stars=False):
        image = Image.new('RGB', (200, 200), (125, 160, 200))
        draw = ImageDraw.Draw(image)
        draw.rectangle((40, 40, 140, 140), fill=color)
        draw.rectangle((40, 141, 140, 190), fill=(40, 60, 70))
        if stars:
            for x in range(50, 135, 9):
                for y in range(50, 135, 9):
                    draw.rectangle((x, y, x+2, y+2), fill=(20, 65, 55))
        camera = {'face_points': [('north', [
            {'screenX': x, 'screenY': y, 'isInScreen': True}
            for x, y in ((40, 40), (140, 40), (140, 140), (40, 140))])]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'frame.png'
            image.save(path)
            return portal_pixels(path, camera)

    def test_support_and_white_surface_are_rejected(self):
        result = self.measure((255, 255, 255))
        self.assertFalse(result['visible'])
        self.assertEqual(1., result['white_ratio'])
        self.assertEqual(0, result['dark_pixels'])

    def test_dark_featureless_surface_and_sky_are_rejected(self):
        self.assertFalse(self.measure((10, 10, 10))['visible'])
        self.assertFalse(self.measure((125, 160, 200))['visible'])
        self.assertFalse(self.measure((62, 78, 40))['visible'])

    def test_colored_star_surface_has_independent_presence(self):
        result = self.measure((2, 2, 2), stars=True)
        self.assertTrue(result['visible'])
        self.assertGreater(result['colored_dark_ratio'], .005)


if __name__ == '__main__':
    unittest.main()
