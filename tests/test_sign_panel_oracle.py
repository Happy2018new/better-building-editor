"""Board isolation rejects terrain, and blank controls retain the 20 cutoff."""
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from sign_panel_oracle import wooden_rectangle, isolate, baseline_control, corresponding_text


class SignPanelOracleTests(unittest.TestCase):
    def test_separate_terrain_runs_do_not_expand_board(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'blank.png'
            image = Image.new('RGB', (220, 150), (100, 170, 240))
            draw = ImageDraw.Draw(image)
            draw.rectangle((30, 45, 129, 114), fill=(140, 100, 60))
            draw.rectangle((20, 10, 139, 19), fill=(140, 100, 60))
            draw.rectangle((160, 90, 215, 119), fill=(90, 60, 30))
            # Terrain can touch a few rows without being part of the broad board.
            draw.rectangle((130, 105, 215, 114), fill=(90, 60, 30))
            image.save(path)
            panel = wooden_rectangle(path, (0, 0, 220, 150))
            self.assertEqual((30, 45, 130, 115), panel)
            mask = Image.new('L', image.size)
            ImageDraw.Draw(mask).rectangle((50, 60, 90, 80), fill=255)
            mask.putpixel((180, 100), 255)
            self.assertEqual(41 * 21, isolate(mask, panel).histogram()[255])

    def test_missing_wood_is_indeterminate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            Image.new('RGB', (60, 40), (100, 170, 240)).save(root / 'blank.png')
            panel = wooden_rectangle(root / 'blank.png', (0, 0, 60, 40))
            self.assertIsNone(panel)
            result = baseline_control(root / 'blank.png', root / 'blank.png',
                                      (0, 0, 60, 40), panel, root / 'delta.png')
            self.assertFalse(result['passed'])
            self.assertFalse(result['determinate'])

    def test_baseline_control_detects_neutral_changes_outside_native_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blank = Image.new('RGB', (100, 80), (140, 100, 60))
            blank.save(root / 'blank.png')
            shown = blank.copy()
            draw = ImageDraw.Draw(shown)
            draw.rectangle((30, 20, 60, 40), fill=(0, 180, 0))
            shown.putpixel((75, 60), (161, 121, 81))
            shown.putpixel((76, 60), (160, 120, 80))
            shown.save(root / 'shown.png')
            panel = (0, 0, 100, 80)
            excluded = corresponding_text((30, 20, 61, 41), panel, panel)
            result = baseline_control(root / 'shown.png', root / 'blank.png',
                                      (0, 0, 100, 80), panel, root / 'delta.png', excluded)
            self.assertFalse(result['passed'])
            self.assertEqual(1, result['changed_pixels'])
            self.assertEqual(20, result['minimum_difference'])


if __name__ == '__main__':
    unittest.main()
