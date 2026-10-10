import sys
import unittest
from unittest.mock import patch
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_entity_appearance_visuals import LOAD, comparison, cleanup_native_fixture


class EntityAppearanceVisualTests(unittest.TestCase):
    def test_preflight_failure_does_not_cleanup_nonexistent_native_fixture(self):
        with patch('verify_entity_appearance_visuals.execute', return_value=False) as execute:
            self.assertEqual(cleanup_native_fixture(object()), {'created': False})
            self.assertEqual(execute.call_count, 1)

    def test_partial_native_setup_still_invokes_fixture_cleanup(self):
        with patch('verify_entity_appearance_visuals.execute', side_effect=[True, {'cleaned': True}]) as execute:
            self.assertEqual(cleanup_native_fixture(object()), {'cleaned': True})
            self.assertEqual(execute.call_count, 2)

    def test_native_and_builtin_load_code_compile(self):
        for source in ('native', 'synthetic'):
            compile(LOAD % ('bed_silver', source), '<entity-appearance-load>', 'exec')

    def test_pixel_oracle_rejects_missing_shifted_and_wrong_color_models(self):
        reference = Image.new('RGB', (100, 100), 'black')
        ImageDraw.Draw(reference).rectangle((20, 15, 69, 84), fill=(55, 135, 205))
        mask = Image.new('L', reference.size)
        ImageDraw.Draw(mask).rectangle((20, 15, 69, 84), fill=255)
        self.assertTrue(comparison(reference, mask, reference, mask)['passed'])
        empty = Image.new('L', reference.size)
        self.assertFalse(comparison(reference, mask, reference, empty)['passed'])
        moved = Image.new('RGB', reference.size)
        moved_mask = Image.new('L', reference.size)
        moved.paste(reference, (25, 0))
        moved_mask.paste(mask, (25, 0))
        self.assertFalse(comparison(reference, mask, moved, moved_mask)['passed'])
        wrong = reference.copy()
        ImageDraw.Draw(wrong).rectangle((20, 15, 69, 84), fill=(220, 30, 40))
        self.assertFalse(comparison(reference, mask, wrong, mask)['passed'])


if __name__ == '__main__':
    unittest.main()
