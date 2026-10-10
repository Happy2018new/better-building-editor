import sys
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_snow_plant_visibility import (PROJECTION_SOURCE, changed, compare_controls, green_mask,
                                         projection_source_matches, scope_checks)


def frame(image):
    blank = Image.new('RGB', image.size)
    presence = changed(image, blank)
    return {'image': image, 'object': presence,
            'green': ImageChops.multiply(green_mask(image), presence)}


def controls():
    plant = Image.new('RGB', (80, 120))
    draw = ImageDraw.Draw(plant)
    draw.rectangle((28, 10, 49, 101), fill=(35, 155, 45))
    for y in range(12, 100, 7):
        draw.line((30, y, 47, y), fill=(55, 205, 60), width=2)
    values = {}
    for height, top in ((0, 95), (5, 48)):
        snow = Image.new('RGB', plant.size)
        ImageDraw.Draw(snow).rectangle((14, top, 65, 110), fill=(200, 210, 220))
        visible = changed(plant, Image.new('RGB', plant.size))
        ImageDraw.Draw(visible).rectangle((0, top, 79, 119), fill=0)
        covered = snow.copy()
        covered.paste(plant, mask=visible)
        values[height] = (frame(snow), frame(covered))
    return frame(plant), values


class SnowPlantVisibilityTests(unittest.TestCase):
    def test_projection_cache_acceptance_requires_exact_current_source(self):
        source = {'editor_id': 1, 'document_id': 2, 'fixture': 'snow.fern.covered.5',
                  'nonce': 3, 'serial': 4, 'model': 'native_snow_model',
                  'work_current': True, 'cache_current': True, 'origin_current': True}
        self.assertTrue(projection_source_matches(source, source))
        for field, value in (('editor_id', 9), ('document_id', 9), ('fixture', 'garden'),
                             ('nonce', 9), ('serial', 9), ('model', 'old_model'),
                             ('work_current', False), ('cache_current', False), ('origin_current', False)):
            with self.subTest(field=field):
                stale = dict(source, **{field: value})
                self.assertFalse(projection_source_matches(stale, source))
        compile(PROJECTION_SOURCE, '<projection-source>', 'exec')

    def test_two_height_occlusion_and_preserved_upper_foliage_pass(self):
        plant, values = controls()
        sampled = {('fern', 'plant', 0): plant}
        for height, (snow, covered) in values.items():
            result = compare_controls(plant, snow, covered, height)
            self.assertTrue(result['passed'], result)
            sampled[('fern', 'snow', height)] = snow
            sampled[('fern', 'covered', height)] = covered
        result = scope_checks(sampled, ('fern',), (0, 5))
        self.assertTrue(result['passed'], result)

    def test_opaque_snow_with_no_foliage_is_not_a_pass(self):
        plant, values = controls()
        snow, unused = values[5]
        result = compare_controls(plant, snow, snow, 5)
        self.assertFalse(result['passed'])
        self.assertIn('plant_contributes_beyond_snow', result['failures'])
        self.assertIn('upper_foliage_retained', result['failures'])

    def test_nonempty_green_foliage_without_snow_occlusion_fails(self):
        plant, values = controls()
        snow, unused = values[5]
        covered = snow['image'].copy()
        covered.paste(plant['image'], mask=plant['object'])
        result = compare_controls(plant, snow, frame(covered), 5)
        self.assertGreater(frame(covered)['green'].histogram()[255], 100)
        self.assertFalse(result['passed'])
        self.assertIn('high_snow_occludes_lower_foliage', result['failures'])

    def test_shifted_foliage_fails_position_and_upper_match(self):
        plant, values = controls()
        snow, covered = values[5]
        shifted = snow['image'].copy()
        portion = plant['image'].crop((28, 10, 50, 48))
        shifted.paste(portion, (46, 10))
        result = compare_controls(plant, snow, frame(shifted), 5)
        self.assertFalse(result['passed'])
        self.assertIn('foliage_stays_at_standalone_position', result['failures'])

    def test_missing_snow_cannot_pass_by_showing_the_whole_plant(self):
        plant, values = controls()
        snow, unused = values[5]
        result = compare_controls(plant, snow, plant, 5)
        self.assertFalse(result['passed'])
        self.assertIn('snow_stays_at_control_position', result['failures'])

    def test_unobservable_standalone_or_snow_control_is_explicit(self):
        plant, values = controls()
        snow, covered = values[5]
        blank = frame(Image.new('RGB', plant['image'].size))
        for reference, snow_control in ((blank, snow), (plant, blank)):
            with self.subTest(plant_visible=reference is plant):
                result = compare_controls(reference, snow_control, covered, 5)
                self.assertFalse(result['valid_baseline'])
                self.assertFalse(result['passed'])
                self.assertIn('observable_controls', result['failures'])

    def test_one_height_is_partial_and_cannot_claim_full_acceptance(self):
        plant, values = controls()
        snow, covered = values[5]
        sampled = {('fern', 'plant', 0): plant,
                   ('fern', 'snow', 5): snow, ('fern', 'covered', 5): covered}
        result = scope_checks(sampled, ('fern',), (5,))
        self.assertFalse(result['required_heights_complete'])
        self.assertFalse(result['passed'])

    def test_scopes_can_disagree_and_remain_independent(self):
        plant, values = controls()
        editor = {('fern', 'plant', 0): plant}
        projection = {('fern', 'plant', 0): plant}
        for height, (snow, covered) in values.items():
            editor[('fern', 'snow', height)] = snow
            editor[('fern', 'covered', height)] = covered
            projection[('fern', 'snow', height)] = snow
            projection[('fern', 'covered', height)] = snow
        self.assertTrue(scope_checks(editor, ('fern',), (0, 5))['passed'])
        self.assertFalse(scope_checks(projection, ('fern',), (0, 5))['passed'])


if __name__ == '__main__':
    unittest.main()
