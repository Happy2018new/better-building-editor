"""Colored snow flowers and separate projection scopes retain real failures."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_snow_catalogue_visuals import (frame_for, compare_world, summarize,
                                         snow_control_matches, native_boundary, compare_exposed)
from camera_projection import project_points
from verify_snow_plant_visibility import convex_hull
from verify_snow_plant_visibility import cross_assets


class SnowCatalogueVisualTests(unittest.TestCase):
    def test_unregistered_static_plants_keep_pixel_checks_without_proxy_alpha(self):
        with tempfile.TemporaryDirectory() as directory:
            session = {'game_executable': str(Path(directory)/'Minecraft.Windows.exe')}
            for plant in ('poppy', 'firefly_bush', 'closed_eyeblossom'):
                with self.subTest(plant=plant):
                    self.assertIsNone(cross_assets(session, plant))

    def test_registered_proxy_uses_the_selected_version_source_and_rejects_missing_record(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            session = {'game_executable': str(root/'Minecraft.Windows.exe')}
            source = root/'static_plant_sources_nemc_next.json'
            source.write_text(json.dumps({'plants': {}}), encoding='utf8')
            with patch('generate_static_plant_proxies.SOURCE', source):
                with self.assertRaisesRegex(ValueError, 'no versioned alpha source: brown_mushroom'):
                    cross_assets(session, 'brown_mushroom')

    def capture(self, path, color, shifted=False):
        image = Image.new('RGB', (80, 80))
        x = 45 if shifted else 20
        ImageDraw.Draw(image).rectangle((x, 10, x+15, 50), fill=color)
        image.save(path)
        return {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}

    def test_colored_flower_pixels_are_kept_and_shift_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blank = self.capture(root/'blank.png', (0, 0, 0))
            native = self.capture(root/'native.png', (230, 40, 65))
            same = self.capture(root/'same.png', (230, 40, 65))
            moved = self.capture(root/'moved.png', (230, 40, 65), True)
            expected = frame_for(native, blank, (0, 0, 80, 80))
            self.assertEqual(656, expected['object'].histogram()[255])
            self.assertTrue(compare_world(expected, frame_for(same, blank, (0, 0, 80, 80)), False)['passed'])
            self.assertFalse(compare_world(expected, frame_for(moved, blank, (0, 0, 80, 80)), False)['passed'])

    def test_modified_saved_image_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'native.png'
            record = self.capture(path, (230, 40, 65))
            self.capture(path, (30, 230, 65))
            with self.assertRaisesRegex(ValueError, 'capture changed'):
                frame_for(record, record, (0, 0, 80, 80))

    def test_full_success_does_not_accept_missing_failure(self):
        rows = []
        for kind in ('plant', 'snow', 'covered'):
            row = {'plant': 'poppy', 'kind': kind, 'height': 0,
                   'comparisons': {'full': {'passed': True}, 'missing': {'passed': kind != 'covered'}}}
            if kind == 'covered':
                row['editor_controls'] = {'passed': True}
            rows.append(row)
        report = {'plants': ['poppy'], 'heights': [0], 'modes': ['full', 'missing'],
                  'rows': rows, 'restored': True, 'source_assets_stable': True}
        summarize(report)
        self.assertTrue(report['completed'])
        self.assertTrue(report['scopes']['full']['passed'])
        self.assertFalse(report['scopes']['missing']['passed'])
        self.assertFalse(report['passed'])
        self.assertFalse(report['all_current_plants_and_heights_sampled'])

    def test_duplicate_cases_and_unverified_assets_cannot_pass(self):
        rows = []
        for kind in ('plant', 'snow', 'covered'):
            row = {'plant': 'poppy', 'kind': kind, 'height': 0,
                   'comparisons': {'full': {'passed': True}}}
            if kind == 'covered':
                row['editor_controls'] = {'passed': True}
            rows.append(row)
        report = {'plants': ['poppy'], 'heights': [0], 'modes': ['full'],
                  'rows': rows, 'restored': True}
        summarize(report)
        self.assertTrue(report['completed'])
        self.assertFalse(report['passed'])
        report['source_assets_stable'] = True
        summarize(report)
        self.assertTrue(report['passed'])
        rows.append(dict(rows[-1]))
        summarize(report)
        self.assertFalse(report['completed'])
        self.assertFalse(report['passed'])

    def test_shared_snow_control_requires_identical_public_input(self):
        source = {'front': ['minecraft:snow_layer', 0], 'back': ['minecraft:air', 0],
                  'focus': [1, 1, 1], 'fixture': 'test.layers.snow', 'fixture_schema': 3,
                  'metadata': {'size': [3, 3, 3], 'blocks': 1, 'name': 'Snow plant visibility check'},
                  'registry_fingerprint': 'current', 'registry_version': 'NEMC 3.9.0.401155',
                  'runtime_minecraft_version': '1.21.120.0', 'render_layout_version': 2}
        self.assertTrue(snow_control_matches(source, dict(source)))
        for key in ('front', 'back', 'focus', 'fixture_schema', 'registry_fingerprint', 'metadata'):
            with self.subTest(key=key):
                changed = dict(source)
                changed[key] = None
                self.assertFalse(snow_control_matches(changed, source))

    def test_fixed_native_roi_rejects_top_contact_but_keeps_root_band(self):
        size = (160, 160)
        pose = {'position': (.5, .5, 4.), 'target': (.5, .5, .5), 'rotation': (0., 0., 0.)}
        corners = [(x, y, z) for x in (0., 1.) for y in (0., 1.) for z in (0., 1.)]
        projected = project_points(corners, pose['position'], pose['target'], size, 67.8, 0.)
        roi = Image.new('L', size)
        ImageDraw.Draw(roi).polygon(convex_hull((p['screenX'], p['screenY']) for p in projected), fill=255)
        record = {'world_base': (0., 0., 0.), 'camera': pose, 'calibration': {'vertical_fov': 67.8}}
        for y, expected in ((1., False), (0., True)):
            point = project_points([(0., y, 1.)], pose['position'], pose['target'], size, 67.8, 0.)[0]
            frame = {'object': Image.new('L', size)}
            x, screen_y = int(point['screenX']), int(point['screenY'])
            ImageDraw.Draw(frame['object']).rectangle((x, screen_y, x+1, screen_y+1), fill=255)
            result = native_boundary(frame, roi, record, (0, 0, *size), size)
            self.assertEqual(expected, result['passed'])
            self.assertEqual(expected, result['clipped_boundary_pixels'] == 0)

    def test_large_snow_mask_cannot_dilute_misplaced_flower_failure(self):
        snow = {'object': Image.new('L', (100, 100))}
        ImageDraw.Draw(snow['object']).rectangle((5, 45, 94, 94), fill=255)
        native = {'object': snow['object'].copy(), 'image': snow['object'].copy()}
        actual = {'object': snow['object'].copy(), 'image': snow['object'].copy()}
        ImageDraw.Draw(native['object']).rectangle((20, 10, 29, 35), fill=255)
        ImageDraw.Draw(actual['object']).rectangle((60, 10, 69, 35), fill=255)
        comparison = compare_world(native, actual, False)
        self.assertTrue(comparison['passed'])
        compare_exposed(comparison, native, actual, snow)
        self.assertFalse(comparison['passed'])
        self.assertEqual(0., comparison['masks']['exposed_plant']['recall'])
        self.assertEqual(0., comparison['masks']['exposed_plant']['precision'])

    def test_fully_occluded_native_plant_rejects_stray_proxy_pixels(self):
        snow = {'object': Image.new('L', (100, 100))}
        ImageDraw.Draw(snow['object']).rectangle((5, 30, 94, 94), fill=255)
        native = {'object': snow['object'].copy(), 'image': snow['object'].copy()}
        actual = {'object': snow['object'].copy(), 'image': snow['object'].copy()}
        comparison = compare_world(native, actual, False)
        self.assertTrue(compare_exposed(comparison, native, actual, snow)['passed'])
        ImageDraw.Draw(actual['object']).rectangle((45, 10, 54, 20), fill=255)
        comparison = compare_world(native, actual, False)
        self.assertTrue(comparison['passed'])
        self.assertFalse(compare_exposed(comparison, native, actual, snow)['passed'])


if __name__ == '__main__':
    unittest.main()
