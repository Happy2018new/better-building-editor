"""The visual suite rejects absent, undersized, shifted and uncalibrated plants."""
import json
from pathlib import Path
import sys
import unittest

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_centered_snow_profiles import shape_metrics, selected_heights, world_alpha
from generate_centered_plant_profiles import PROFILE, outputs
from projection.debug_snow_blueprints import NAMES


class CenteredSnowVisualTests(unittest.TestCase):
    def test_oracle_presence_cannot_pass_an_empty_actual_capture(self):
        expected = Image.new('L', (128, 128))
        ImageDraw.Draw(expected).rectangle((30, 30, 80, 100), fill=255)
        absent = Image.new('L', expected.size)
        self.assertFalse(shape_metrics(expected, absent)['passed'])
        self.assertTrue(shape_metrics(expected, expected)['passed'])
        shifted = Image.new('L', expected.size)
        ImageDraw.Draw(shifted).rectangle((0, 30, 50, 100), fill=255)
        self.assertFalse(shape_metrics(expected, shifted)['passed'])

    def test_tiny_controls_are_not_accepted_as_visible_plant_evidence(self):
        tiny = Image.new('L', (128, 128))
        ImageDraw.Draw(tiny).rectangle((30, 30, 33, 33), fill=255)
        self.assertFalse(shape_metrics(tiny, tiny)['passed'])
        empty = Image.new('L', tiny.size)
        self.assertTrue(shape_metrics(empty, empty)['passed'])

    def test_each_plant_matrix_includes_thin_snow_and_full_burial(self):
        profile = json.loads(PROFILE.read_bytes())
        for name in NAMES:
            heights = selected_heights(name)
            self.assertIn(0, heights)
            self.assertIn(7, heights)
            self.assertEqual(tuple(sorted(set(heights))), heights)
            if name in profile['plants']:
                plant = profile['plants'][name]
                top = plant['mesh']['height']*(1.-plant['alpha_bounds'][1]/16.)
                before = [height for height in heights if (height+1)/8. < top]
                after = [height for height in heights if (height+1)/8. >= top]
                self.assertTrue(before and after, name)

    def test_world_alpha_is_visible_inside_cell_and_disappears_after_burial(self):
        profile = json.loads(PROFILE.read_bytes())
        files = outputs(profile)
        model = files[ROOT/'resource_pack/models/netease_block/centered_poppy.json']
        texture = Image.new('RGBA', (16, 16))
        ImageDraw.Draw(texture).rectangle((5, 5, 11, 15), fill=(255, 40, 30, 255))
        pose = {'position': (-1.5, 1.7, -2.), 'target': (.5, .5, .5), 'rotation': (0, 0, 0)}
        calibration = {'vertical_fov': 70.}
        dry = world_alpha(model, texture, pose, (1024, 768), (256, 192, 768, 576), (0, 0, 0), calibration)
        thin = world_alpha(model, texture, pose, (1024, 768), (256, 192, 768, 576), (0, 0, 0), calibration, 0)
        covered = world_alpha(model, texture, pose, (1024, 768), (256, 192, 768, 576), (0, 0, 0), calibration, 5)
        self.assertIsNotNone(dry.getbbox())
        self.assertIsNotNone(thin.getbbox())
        self.assertIsNone(covered.getbbox())
        self.assertTrue(all(0 < edge < size for edge, size in zip(dry.getbbox(), (512, 384, 512, 384))))


if __name__ == '__main__':
    unittest.main()
