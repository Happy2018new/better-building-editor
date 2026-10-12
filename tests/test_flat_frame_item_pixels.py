"""Reject blank items and an opaque/half-alpha result masquerading as 0.2."""
from copy import deepcopy
import hashlib
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from flat_frame_item_visual_checks import alpha_measure, capture_payload, content_mask
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

    def test_mismatched_native_dimensions_are_rejected_before_scoring(self):
        with TemporaryDirectory() as directory:
            first, second = [Path(directory) / (name + '.png') for name in ('full', 'resized')]
            Image.new('RGB', (20, 20), (100, 100, 100)).save(first)
            Image.new('RGB', (21, 20), (220, 220, 220)).save(second)
            crop, mask = (0, 0, 20, 20), Image.new('L', (20, 20), 255)
            for call in (lambda: content_mask(first, second, crop),
                         lambda: alpha_measure(first, second, first, crop, mask),
                         lambda: layer_measure(first, second, first, first, crop, mask)):
                with self.subTest(call=call), self.assertRaises(ValueError):
                    call()

    def test_invalid_crop_and_misaligned_mask_cannot_score_padded_pixels(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'frame.png'
            Image.new('RGB', (20, 20), (100, 100, 100)).save(path)
            for crop in ((-1, 0, 19, 20), (0, 0, 21, 20), (0, 0, 0, 20),
                         (0., 0, 20, 20), (False, 0, 20, 20)):
                with self.subTest(crop=crop), self.assertRaises(ValueError):
                    content_mask(path, path, crop)
            for mask in (Image.new('L', (19, 20), 255), Image.new('RGB', (20, 20), 'white')):
                with self.subTest(mask=mask.size), self.assertRaises(ValueError):
                    alpha_measure(path, path, path, (0, 0, 20, 20), mask)
                with self.subTest(compositor=mask.size), self.assertRaises(ValueError):
                    layer_measure(path, path, path, path, (0, 0, 20, 20), mask)

    def test_capture_wrapper_and_receipt_bind_exact_decoded_bytes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / 'frame.png'
            other = Path(directory) / 'other.png'
            Image.new('RGB', (20, 20), (100, 100, 100)).save(path)
            Image.new('RGB', (20, 20), (200, 200, 200)).save(other)
            payload = path.read_bytes()
            record = {'path': str(path), 'bytes': len(payload), 'size': [20, 20],
                      'sha256': hashlib.sha256(payload).hexdigest(), 'mime': 'image/png'}
            record['capture'] = dict(record, width=20, height=20, frame={'width': 20, 'height': 20})
            frozen = capture_payload(record)
            variants = []
            for mutate in (lambda row: row.update(path=str(other)),
                           lambda row: row.update(sha256='0' * 64),
                           lambda row: row['capture'].update(bytes=0),
                           lambda row: row['capture']['frame'].update(width=21)):
                variant = deepcopy(record)
                mutate(variant)
                variants.append(variant)
            for variant in variants:
                with self.subTest(variant=variant), self.assertRaises(ValueError):
                    capture_payload(variant)
            Image.new('RGB', (20, 20), (200, 200, 200)).save(path)
            with Image.open(frozen) as image:
                self.assertEqual((100, 100, 100), image.getpixel((0, 0)))
            with self.assertRaises(ValueError):
                capture_payload(record)


if __name__ == '__main__':
    unittest.main()
