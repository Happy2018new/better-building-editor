import sys
import json
import hashlib
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_snow_plant_visibility import (PROJECTION_SOURCE, changed, compare_controls, green_mask,
                                         compare_native, projection_source_matches, scope_checks,
                                         NATIVE_SETUP, NATIVE_MUTATE, NATIVE_CLEANUP,
                                         snow_plant_mask, editor_cross_above_snow, capture_frame)
from reanalyze_snow_visibility import stored_upper


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
    def test_world_roi_rejects_changed_background_foliage_outside_the_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            shown_path, hidden_path = Path(directory)/'shown.png', Path(directory)/'hidden.png'
            shown = Image.new('RGB', (80, 80))
            ImageDraw.Draw(shown).rectangle((30, 30, 49, 49), fill=(35, 155, 45))
            ImageDraw.Draw(shown).rectangle((0, 0, 9, 9), fill=(35, 155, 45))
            shown.save(shown_path)
            Image.new('RGB', shown.size).save(hidden_path)
            roi = Image.new('L', shown.size)
            ImageDraw.Draw(roi).rectangle((20, 20, 59, 59), fill=255)
            sampled = capture_frame(shown_path, (0, 0, 80, 80), hidden_path, segmented=True, roi=roi)
            self.assertEqual((30, 30, 50, 50), sampled['green'].getbbox())
            self.assertEqual(400, sampled['green'].histogram()[255])

    def test_replay_preserves_upper_geometry_and_rejects_changed_mask_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'upper.png'
            mask = Image.new('L', (80, 80))
            ImageDraw.Draw(mask).rectangle((30, 30, 49, 49), fill=255)
            mask.save(path)
            record = {'5': {'mask': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}}
            restored = stored_upper(record, mask.size)
            self.assertIsNone(ImageChops.difference(mask, restored[5]).getbbox())
            Image.new('L', mask.size).save(path)
            with self.assertRaises(ValueError):
                stored_upper(record, mask.size)

    def test_three_dimensional_upper_texels_survive_inside_snow_screen_hull(self):
        plant, values = controls()
        snow, covered = values[5]
        snow['geometry'] = plant['object'].copy()
        plant['above_snow'] = {5: plant['object'].copy()}
        ImageDraw.Draw(plant['above_snow'][5]).rectangle((0, 48, 79, 119), fill=0)
        result = compare_controls(plant, snow, covered, 5)
        self.assertTrue(result['passed'], result)
        self.assertFalse(result['fully_occluded_by_snow_control'])
        self.assertFalse(compare_controls(plant, snow, snow, 5)['passed'])

    def test_alpha_bounds_distinguish_short_grass_from_fern_tip_above_high_snow(self):
        state = {'pose': (35., 10., 2.8), 'pan': (0., 0.), 'pivot': (1.5, 1.5, 1.5), 'size': (3, 3, 3)}
        model = json.loads((ROOT/'resource_pack/models/netease_block/preview_fern.json').read_text(encoding='utf8'))
        fern = Image.new('RGBA', (16, 16))
        fern.putpixel((7, 0), (35, 155, 45, 255))
        grass = Image.new('RGBA', (16, 16))
        ImageDraw.Draw(grass).rectangle((0, 2, 15, 15), fill=(35, 155, 45, 255))
        fern_mask = editor_cross_above_snow((0, 0, 465, 213), state, (1, 1, 1), 5, model, fern)
        grass_mask = editor_cross_above_snow((0, 0, 465, 213), state, (1, 1, 1), 5, model, grass)
        self.assertIsNotNone(fern_mask.getbbox())
        self.assertIsNone(grass_mask.getbbox())

    def test_native_segmentation_keeps_dry_grass_and_snow_and_rejects_sky_dirt(self):
        image = Image.new('RGB', (5, 1))
        image.putdata(((145, 129, 77), (35, 155, 45), (195, 200, 205),
                       (150, 185, 235), (145, 110, 75)))
        self.assertEqual([255, 255, 255, 0, 0], list(snow_plant_mask(image).getdata()))
        self.assertEqual([255, 255, 0, 0, 0], list(green_mask(image).getdata()))

    def test_warm_neutral_snow_is_not_mistaken_for_foliage(self):
        image = Image.new('RGB', (4, 1))
        image.putdata(((216, 215, 204), (160, 161, 148),
                       (145, 129, 77), (35, 155, 45)))
        self.assertEqual([0, 0, 255, 255], list(green_mask(image).getdata()))
        self.assertEqual([255, 255, 255, 255], list(snow_plant_mask(image).getdata()))

    def test_high_snow_can_naturally_cover_a_shorter_standalone_plant(self):
        plant, values = controls()
        snow, unused = values[5]
        short = Image.new('RGB', plant['image'].size)
        ImageDraw.Draw(short).rectangle((28, 62, 49, 101), fill=(35, 155, 45))
        result = compare_controls(frame(short), snow, snow, 5)
        self.assertTrue(result['passed'], result)
        self.assertTrue(result['fully_occluded_by_snow_control'])
        self.assertTrue(result['checks']['fully_covered_plant_stays_occluded'])
        visible = snow['image'].copy()
        visible.paste(short, mask=changed(short, Image.new('RGB', short.size)))
        self.assertFalse(compare_controls(frame(short), snow, frame(visible), 5)['passed'])

    def test_native_oracle_rejects_missing_shifted_foliage_and_missing_snow(self):
        plant, values = controls()
        snow, covered = values[5]
        self.assertTrue(compare_native(covered, covered)['passed'])
        self.assertFalse(compare_native(covered, snow)['passed'])
        self.assertFalse(compare_native(covered, plant)['passed'])
        shifted = Image.new('RGB', plant['image'].size)
        shifted.paste(covered['image'], (18, 0))
        self.assertFalse(compare_native(covered, frame(shifted))['passed'])

    def test_native_oracle_allows_foliage_fully_occluded_in_both_images(self):
        unused, values = controls()
        snow, unused = values[5]
        self.assertTrue(compare_native(snow, snow)['passed'])
        extra_plant = snow['image'].copy()
        ImageDraw.Draw(extra_plant).rectangle((28, 10, 49, 45), fill=(35, 155, 45))
        self.assertFalse(compare_native(snow, frame(extra_plant))['passed'])
        compile(NATIVE_SETUP % ((6, -52, 6),), '<native-setup>', 'exec')
        compile(NATIVE_MUTATE % ('fern', 'covered', 5), '<native-mutate>', 'exec')
        compile(NATIVE_CLEANUP, '<native-cleanup>', 'exec')

    def test_projection_cache_acceptance_requires_exact_current_source(self):
        source = {'editor_id': 1, 'document_id': 2, 'fixture': 'snow.fern.covered.5',
                  'nonce': 3, 'serial': 4, 'model': 'native_snow_model',
                  'work_current': True, 'cache_current': True, 'origin_current': True,
                  'path': 'synchronous'}
        self.assertTrue(projection_source_matches(source, source))
        for field, value in (('editor_id', 9), ('document_id', 9), ('fixture', 'garden'),
                             ('nonce', 9), ('serial', 9), ('model', 'old_model'),
                             ('work_current', False), ('cache_current', False), ('origin_current', False),
                             ('path', 'incremental')):
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
