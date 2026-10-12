"""Reject blank items and an opaque/half-alpha result masquerading as 0.2."""
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from flat_frame_item_visual_checks import alpha_measure, content_mask
from analyze_flat_frame_compositor import layer_measure


class FlatItemPixelChecks(unittest.TestCase):
    def test_two_layers_explain_contrast_without_changing_single_layer_gate(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name, color in (('both_full', (100, 100, 100)), ('both_faded', (196, 196, 196)),
                                ('item_faded', (220, 220, 220)), ('body_faded', (220, 220, 220)),
                                ('blank', (250, 250, 250))):
                path = root / (name + '.png')
                Image.new('RGB', (20, 20), color).save(path)
                paths.append(path)
            mask, crop = Image.new('L', (20, 20), 255), (0, 0, 20, 20)
            self.assertFalse(alpha_measure(paths[0], paths[1], paths[4], crop, mask)['passed'])
            result = layer_measure(paths[1], paths[2], paths[3], paths[4], crop, mask)
            self.assertTrue(result['diagnostic_matches_layers'])
            self.assertAlmostEqual(.36, result['equal_color_two_layer_coverage'])
            self.assertEqual(0., result['relative_composition_residual'])

    def test_expected_alpha_is_measured_against_the_hidden_background(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            paths = []
            for name, color in (('full', (150, 100, 50)), ('alpha02', (230, 220, 210)),
                                ('alpha05', (200, 175, 150)), ('hidden', (250, 250, 250))):
                path = root / (name + '.png')
                Image.new('RGB', (20, 20), color).save(path)
                paths.append(path)
            mask = Image.new('L', (20, 20), 255)
            crop = (0, 0, 20, 20)
            correct = alpha_measure(paths[0], paths[1], paths[3], crop, mask)
            self.assertTrue(correct['passed'])
            self.assertAlmostEqual(.2, correct['measured_contrast_gain'])
            self.assertFalse(alpha_measure(paths[0], paths[2], paths[3], crop, mask)['passed'])
            self.assertFalse(alpha_measure(paths[0], paths[0], paths[3], crop, mask)['passed'])
            self.assertFalse(alpha_measure(paths[0], paths[1], paths[3], crop, Image.new('L', (20, 20)))['passed'])

    def test_empty_frame_does_not_pass_an_item_difference_control(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'frame.png'
            Image.new('RGB', (20, 20), (120, 70, 20)).save(path)
            unused, mask = content_mask(path, path, (0, 0, 20, 20))
            self.assertIsNone(mask.getbbox())


if __name__ == '__main__':
    unittest.main()
