import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_chest_occupied_frozen_holdout import cleanup, composite_signal, restoration_matches


class CompositeDiagnosticTests(unittest.TestCase):
    def test_disconnected_native_and_virtual_pieces_both_contribute(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = Image.new('RGB', (140, 80), (230, 230, 230))
            shown = background.copy()
            draw = ImageDraw.Draw(shown)
            draw.rectangle((10, 20, 49, 59), fill=(100, 50, 20))
            draw.rectangle((70, 20, 109, 59), fill=(20, 130, 50))
            shown.save(root/'shown.png')
            background.save(root/'empty.png')
            unused_image, unused_mask, record = composite_signal(
                root/'shown.png', root/'empty.png', (0, 0, 140, 80), root/'signal.png')
            self.assertEqual(3200, record['pixels'])
            self.assertEqual([10, 20, 110, 60], record['world_bounds'])
            with Image.open(root/'signal_mask.png') as mask:
                self.assertEqual(255, mask.getpixel((20, 30)))
                self.assertEqual(255, mask.getpixel((80, 30)))
                self.assertEqual(0, mask.getpixel((60, 30)))

    def test_roi_excludes_unrelated_native_background_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = Image.new('RGB', (140, 80), (230, 230, 230))
            shown = background.copy()
            draw = ImageDraw.Draw(shown)
            draw.rectangle((30, 20, 69, 59), fill=(100, 50, 20))
            draw.rectangle((100, 0, 139, 79), fill=(10, 40, 80))
            shown.save(root/'shown.png')
            background.save(root/'empty.png')
            unused_image, unused_mask, record = composite_signal(
                root/'shown.png', root/'empty.png', (20, 10, 90, 70), root/'signal.png')
            self.assertEqual(1600, record['pixels'])
            self.assertEqual([30, 20, 70, 60], record['world_bounds'])

    def test_small_composite_cannot_pass_positive_control(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            background = Image.new('RGB', (80, 80), (230, 230, 230))
            shown = background.copy()
            ImageDraw.Draw(shown).rectangle((10, 20, 29, 39), fill=(100, 50, 20))
            shown.save(root/'shown.png')
            background.save(root/'empty.png')
            with self.assertRaisesRegex(AssertionError, '400'):
                composite_signal(root/'shown.png', root/'empty.png', (0, 0, 80, 80), root/'signal.png')


class RestorationEvidenceTests(unittest.TestCase):
    def test_cleanup_failure_does_not_skip_later_restore(self):
        seen = []

        def fail():
            seen.append('world')
            raise RuntimeError('independent world restoration failed')

        def restore_player():
            seen.append('player')
            return {'foot': [.5, 74., .5]}

        report = {}
        cleanup([('world', fail), ('player', restore_player)], report)
        self.assertEqual(['world', 'player'], seen)
        self.assertFalse(report['restored'])
        self.assertEqual(['world: RuntimeError: independent world restoration failed'], report['cleanup_errors'])
        self.assertEqual({'foot': [.5, 74., .5]}, report['player_restored'])

    def test_independent_readback_rejects_position_rotation_or_flight_drift(self):
        baseline = {'foot': [.5, 74., .5], 'rotation': [0., 180.], 'can_fly': True, 'flying': False}
        self.assertTrue(restoration_matches(baseline, dict(baseline)))
        for key, value in [('foot', [.5, 73., .5]), ('rotation', [0., 181.]),
                           ('can_fly', False), ('flying', True)]:
            with self.subTest(key=key):
                self.assertFalse(restoration_matches(baseline, dict(baseline, **{key: value})))


if __name__ == '__main__':
    unittest.main()
