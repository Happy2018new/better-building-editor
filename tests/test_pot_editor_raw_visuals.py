"""Reject cropped, blank or divergent raw editor reference pixels."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pot_editor_raw_visuals', ROOT / 'tools/verify_pot_editor_raw_visuals.py')
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


class RawPotEditorOracleTests(unittest.TestCase):
    def compare(self, bounds, raw_present=True, divergent=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            frames = []
            for name in ('production', 'raw', 'hidden'):
                image = Image.new('RGB', (160, 140), '#f6f8fb')
                if name != 'hidden' and (name != 'raw' or raw_present):
                    draw = ImageDraw.Draw(image)
                    draw.rectangle(bounds, fill='#914f3f')
                    draw.rectangle((70, max(bounds[1], 45), 82, min(bounds[3], 80)),
                                   fill='#aa9272' if name == 'production' and divergent else '#592b20')
                path = root / (name + '.png')
                image.save(path)
                frames.append({'path': str(path), 'size': image.size})
            return TOOL.frames(*frames, (10, 10, 150, 130), root)

    def test_same_pixels_still_reject_clipped_body(self):
        result = self.compare((45, 10, 115, 90))
        self.assertTrue(result['pixel_agreement_passed'])
        self.assertFalse(result['framing_passed'])
        self.assertFalse(result['passed'])

    def test_blank_raw_reference_cannot_accept_visible_production(self):
        result = self.compare((45, 35, 115, 100), raw_present=False)
        self.assertFalse(result['raw_positive_control'])
        self.assertFalse(result['passed'])

    def test_same_complete_raw_reference_accepts_actual_viewport(self):
        result = self.compare((45, 35, 115, 100))
        self.assertTrue(result['raw_positive_control'])
        self.assertTrue(result['framing_passed'])
        self.assertEqual(0, result['changed_pixels_over_25'])
        self.assertTrue(result['passed'])

    def test_divergent_artwork_rejects_complete_reference(self):
        result = self.compare((45, 35, 115, 100), divergent=True)
        self.assertTrue(result['framing_passed'])
        self.assertGreater(result['changed_pixels_over_25'], 100)
        self.assertFalse(result['passed'])


if __name__ == '__main__':
    unittest.main()
