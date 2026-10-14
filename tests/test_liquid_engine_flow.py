"""Native diagnostic boundaries must preserve an independently drawn plane."""
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from probe_liquid_engine_flow import isolated_face_map


class NativeFlowBoundaryTests(unittest.TestCase):
    def test_four_corners_and_center_survive_crosshair_occlusion(self):
        image = Image.new('RGB', (400, 300), (80, 160, 230))
        draw = ImageDraw.Draw(image)
        corners = ((130, 60), (270, 60), (300, 240), (100, 240))
        draw.polygon(corners, fill=(160, 0, 160))
        draw.line((195, 150, 205, 150), fill=(0, 255, 0), width=3)
        h, boundary = isolated_face_map(np.asarray(image), False)
        for uv, expected in zip(((0, 0), (1, 0), (1, 1), (0, 1)), corners):
            point = h @ [uv[0], uv[1], 1]
            np.testing.assert_allclose(point[:2] / point[2], expected, atol=1)
        self.assertGreater(boundary['support_pixels'], 20000)

    def test_background_and_small_speck_cannot_define_native_surface(self):
        for pixels in (0, 15):
            image = np.full((100, 100, 3), 127, dtype=np.uint8)
            image[:pixels, :pixels] = (255, 0, 255)
            with self.assertRaises(ValueError):
                isolated_face_map(image, True)


if __name__ == '__main__':
    unittest.main()
