import sys
from pathlib import Path
import unittest

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_spawner_product_r16 import marker_difference, retained_support


class SpawnerAcceptancePixelsTests(unittest.TestCase):
    def test_background_animation_cannot_qualify_missing_marker(self):
        control = Image.new('RGB', (1994, 1105), '#122b34')
        candidate = control.copy()
        ImageDraw.Draw(candidate).rectangle((10, 400, 800, 800), fill='#18ef37')
        self.assertFalse(marker_difference(candidate, control, 'full_mob_spawner_pig_badge')
                         ['observed_badge_difference'])

    def test_focus_requires_expected_presence_color(self):
        control = Image.new('RGB', (1994, 1105), '#122b34')
        candidate = control.copy()
        ImageDraw.Draw(candidate).rectangle((980, 620, 1020, 660), fill='#18ef37')
        self.assertTrue(marker_difference(candidate, control, 'editor_trial_spawner_pig_badge')
                        ['observed_badge_difference'])
        self.assertFalse(marker_difference(candidate, control, 'editor_trial_spawner_unknown_badge')
                         ['observed_badge_difference'])

    def test_focus_scales_with_actual_capture_dimensions(self):
        control = Image.new('RGB', (997, 552), '#122b34')
        candidate = control.copy()
        ImageDraw.Draw(candidate).rectangle((490, 310, 510, 330), fill='#ececea')
        self.assertTrue(marker_difference(candidate, control, 'editor_mob_spawner_empty_badge')
                        ['observed_badge_difference'])

    def test_hidden_empty_frame_cannot_qualify_retained_support(self):
        blank = Image.new('RGB', (1994, 1105), '#f6f8fa')
        self.assertFalse(retained_support(blank)['retained_support_observed'])
        ImageDraw.Draw(blank).rectangle((920, 700, 1040, 820), fill='#147b89')
        self.assertTrue(retained_support(blank)['retained_support_observed'])

    def test_support_outside_focus_cannot_hide_blank_scene(self):
        blank = Image.new('RGB', (1994, 1105), '#f6f8fa')
        ImageDraw.Draw(blank).rectangle((10, 400, 800, 800), fill='#147b89')
        self.assertFalse(retained_support(blank)['retained_support_observed'])

    def test_unknown_source_uses_its_actual_yellow_support(self):
        picture = Image.new('RGB', (1994, 1105), '#f6f8fa')
        ImageDraw.Draw(picture).rectangle((920, 700, 1040, 820), fill='#efbd10')
        self.assertTrue(retained_support(picture, unknown=True)['retained_support_observed'])
        self.assertFalse(retained_support(picture)['retained_support_observed'])


if __name__ == '__main__':
    unittest.main()
