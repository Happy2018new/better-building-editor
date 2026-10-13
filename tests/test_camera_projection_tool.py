import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from camera_projection import project_box_corners, project_points
from verify_debug_blueprints import (INSTALL_PROBE, RESTORE, STATUS,
                                     editor_preview_ready, source_matches)
from verify_missing_neighbor_visuals import CELL_ROIS, compare_complete
from verify_snow_plant_visibility import LOAD
from verify_camera_projection import fit_fov, largest_component, projected_mask, stone_signal
from PIL import Image, ImageChops, ImageDraw


class CameraProjectionTests(unittest.TestCase):
    def test_target_projects_to_viewport_center(self):
        point, = project_points(((0., 0., 0.),), (0., 0., 10.), (0., 0., 0.),
                                (800, 600), 60.)
        self.assertAlmostEqual(point['screenX'], 400.)
        self.assertAlmostEqual(point['screenY'], 300.)
        self.assertEqual(point['depth'], 10.)
        self.assertTrue(point['isInScreen'])

    def test_world_right_and_up_follow_screen_axes(self):
        right, up = project_points(((1., 0., 0.), (0., 1., 0.)),
                                   (0., 0., 10.), (0., 0., 0.), (800, 600), 60.)
        self.assertGreater(right['screenX'], 400.)
        self.assertAlmostEqual(right['screenY'], 300.)
        self.assertAlmostEqual(up['screenX'], 400.)
        self.assertLess(up['screenY'], 300.)

    def test_depth_controls_perspective_and_viewport_aspect(self):
        near, far = project_points(((1., 0., 0.), (1., 0., -10.)),
                                   (0., 0., 10.), (0., 0., 0.), (800, 600), 60.)
        self.assertAlmostEqual(near['screenX'] - 400., (far['screenX'] - 400.) * 2.)
        wide = project_points(((1., 0., 0.),), (0., 0., 10.), (0., 0., 0.),
                              (1200, 600), 60.)[0]
        self.assertAlmostEqual(wide['screenX'] - 600., near['screenX'] - 400.)

    def test_points_behind_camera_are_not_visible(self):
        point, = project_points(((0., 0., 20.),), (0., 0., 10.), (0., 0., 0.),
                                (800, 600), 60.)
        self.assertLess(point['depth'], 0.)
        self.assertFalse(point['isInScreen'])

    def test_box_behind_camera_is_empty_and_crossing_box_is_clipped(self):
        behind = ((-.5, -.5, 12.), (-.5, -.5, 13.), (-.5, .5, 12.), (-.5, .5, 13.),
                  (.5, -.5, 12.), (.5, -.5, 13.), (.5, .5, 12.), (.5, .5, 13.))
        self.assertEqual(project_box_corners(behind, (0., 0., 10.), (0., 0., 0.),
                                             (800, 600), 60.), [])
        crossing = ((-.5, -.5, 9.), (-.5, -.5, 11.), (-.5, .5, 9.), (-.5, .5, 11.),
                    (.5, -.5, 9.), (.5, -.5, 11.), (.5, .5, 9.), (.5, .5, 11.))
        clipped = project_box_corners(crossing, (0., 0., 10.), (0., 0., 0.),
                                      (800, 600), 60.)
        self.assertEqual(len(clipped), 8)
        self.assertTrue(all(point['depth'] >= .05 for point in clipped))

    def test_invalid_viewport_or_degenerate_camera_fails_explicitly(self):
        for args in (((0., 0., 0.), (0., 0., 10.), (0., 0., 0.), (800, 600), 180.),
                     ((0., 0., 0.), (0., 0., 0.), (0., 0., 0.), (800, 600), 60.),
                     ((0., 0., 0.), (0., 0., 10.), (0., 0., 0.), (0, 600), 60.)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                project_points((args[0],), args[1], args[2], args[3], args[4])

    def test_calibration_recovers_native_cube_fov(self):
        pose = {'position': (0., 0., 6.), 'target': (0., 0., 0.)}
        cube = projected_mask(pose, (800, 600), 80.)
        fitted = fit_fov(cube, pose)
        self.assertLessEqual(abs(fitted['vertical_fov'] - 80.), 1.)
        self.assertEqual(fitted['boundary_rms_pixels'], 0.)
        self.assertEqual(fitted['mask_iou'], 1.)

    def test_calibration_crop_score_matches_full_raster_search(self):
        poses = ({'position': (0., 0., 6.), 'target': (0., 0., 0.)},
                 {'position': (6., -3., 0.), 'target': (0., 0., 0.)})
        for pose in poses:
            with self.subTest(pose=pose):
                actual = projected_mask(pose, (320, 180), 66.3)
                draw = ImageDraw.Draw(actual)
                draw.rectangle((2, 2, 8, 7), fill=255)
                draw.rectangle((158, 85, 161, 89), fill=0)
                bounds, best = actual.getbbox(), None
                for step in range(300, 1301):
                    predicted = projected_mask(pose, actual.size, step / 10.)
                    error = sum((bounds[i] - predicted.getbbox()[i]) ** 2 for i in range(4))
                    union = ImageChops.lighter(actual, predicted).histogram()[255]
                    intersection = ImageChops.multiply(actual, predicted).histogram()[255]
                    score = (-intersection / max(1, union), error)
                    if best is None or score < best[0]:
                        best = (score, step / 10., predicted.getbbox())
                fitted = fit_fov(actual, pose)
                self.assertEqual(fitted['vertical_fov'], best[1])
                self.assertEqual(fitted['mask_iou'], -best[0][0])
                self.assertEqual(fitted['predicted_bounds'], best[2])

    def test_calibration_crop_score_preserves_viewport_clipping(self):
        pose = {'position': (0., 0., .75), 'target': (0., 0., 0.)}
        actual = projected_mask(pose, (120, 80), 110.)
        ImageDraw.Draw(actual).rectangle((0, 20, 20, 35), fill=0)
        for fov in (30., 60., 110., 130.):
            with self.subTest(fov=fov):
                predicted = projected_mask(pose, actual.size, fov)
                union = ImageChops.lighter(actual, predicted).histogram()[255]
                intersection = ImageChops.multiply(actual, predicted).histogram()[255]
                fitted = fit_fov(actual, pose, fov)
                self.assertEqual(fitted['mask_iou'], intersection / max(1, union))
                self.assertEqual(fitted['predicted_bounds'], predicted.getbbox())

    def test_calibration_excludes_disconnected_background_changes(self):
        mask = Image.new('L', (100, 80))
        draw = ImageDraw.Draw(mask)
        draw.rectangle((40, 30, 59, 49), fill=255)
        draw.rectangle((1, 1, 5, 4), fill=255)
        self.assertEqual(largest_component(mask).getbbox(), (40, 30, 60, 50))

    def _stone_signal(self, shown, hidden):
        with tempfile.TemporaryDirectory() as directory:
            shown_path, hidden_path = (Path(directory) / name for name in ('shown.png', 'hidden.png'))
            shown.save(shown_path)
            hidden.save(hidden_path)
            return stone_signal(shown_path, hidden_path)

    def test_calibration_rejects_unchanged_connected_neutral_background(self):
        hidden = Image.new('RGB', (200, 160), (20, 60, 20))
        ImageDraw.Draw(hidden).rectangle((75, 95, 91, 114), fill=(110, 110, 110))
        shown = hidden.copy()
        ImageDraw.Draw(shown).rectangle((65, 50, 114, 94), fill=(120, 120, 120))
        mask = self._stone_signal(shown, hidden)
        self.assertEqual(mask.getbbox(), (65, 50, 115, 95))
        self.assertEqual(mask.getpixel((80, 108)), 0)

    def test_calibration_fills_enclosed_cursor_and_texture_holes(self):
        hidden = Image.new('RGB', (200, 160), (20, 60, 20))
        shown = hidden.copy()
        ImageDraw.Draw(shown).rectangle((65, 50, 114, 94), fill=(120, 120, 120))
        for image in (shown, hidden):
            draw = ImageDraw.Draw(image)
            draw.rectangle((83, 68, 99, 70), fill=(245, 245, 245))
            draw.rectangle((90, 61, 92, 78), fill=(245, 245, 245))
        ImageDraw.Draw(shown).rectangle((72, 56, 78, 61), fill=(110, 70, 40))
        mask = self._stone_signal(shown, hidden)
        self.assertEqual(mask.getbbox(), (65, 50, 115, 95))
        self.assertEqual(mask.getpixel((91, 69)), 255)
        self.assertEqual(mask.getpixel((75, 58)), 255)

    def test_calibration_preserves_open_missing_edge_notch(self):
        hidden = Image.new('RGB', (200, 160), (20, 60, 20))
        shown = hidden.copy()
        draw = ImageDraw.Draw(shown)
        draw.rectangle((65, 50, 114, 94), fill=(120, 120, 120))
        draw.rectangle((93, 49, 100, 68), fill=(20, 60, 20))
        mask = self._stone_signal(shown, hidden)
        self.assertEqual(mask.getbbox(), (65, 50, 115, 95))
        self.assertEqual(mask.getpixel((96, 57)), 0)
        self.assertEqual(mask.getpixel((88, 57)), 255)

    def test_context_baseline_must_match_independent_complete_geometry(self):
        native = Image.new('RGB', (100, 80))
        ImageDraw.Draw(native).rectangle((30, 30, 69, 49), fill=(150, 100, 60))
        left, right = Image.new('L', native.size), Image.new('L', native.size)
        ImageDraw.Draw(left).rectangle((10, 20, 49, 59), fill=255)
        ImageDraw.Draw(right).rectangle((50, 20, 89, 59), fill=255)
        self.assertTrue(compare_complete(native, native, (left, right), 16, 80)['passed'])
        shifted = Image.new('RGB', native.size)
        ImageDraw.Draw(shifted).rectangle((10, 30, 49, 49), fill=(150, 100, 60))
        report = compare_complete(native, shifted, (left, right), 16, 80)
        self.assertTrue(report['valid_baseline'])
        self.assertFalse(report['passed'])

    def test_invisible_complete_geometry_cannot_validate_context(self):
        blank = Image.new('RGB', (100, 80))
        roi = Image.new('L', blank.size, 255)
        report = compare_complete(blank, blank, (roi, roi), 16, 80)
        self.assertFalse(report['valid_baseline'])
        self.assertFalse(report['passed'])


class BlueprintSourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.metadata = {'name': 'Snow plant visibility check', 'size': [8, 6, 8], 'blocks': 1}
        self.state = {'metadata': self.metadata, 'editor_id': 21, 'document_id': 34,
                      'current_source': True, 'all_parts_current': True,
                      'preview_error': '', 'page': 'workspace', 'preview_pending': False,
                      'running': False, 'dirty': 0, 'mounting': False, 'edit_active': False,
                      'io_active': False, 'model_revision_current': True, 'model_name': 'current_model',
                      'renderer_active': True, 'renderer_age': .1, 'native_calls': [],
                      'parts': [{'pending': False, 'cache_current': True, 'name': 'current_model'}]}

    def test_current_document_and_geometry_are_required(self):
        self.assertTrue(source_matches(self.state, self.metadata, 21, 34))
        for field, value in (('editor_id', 22), ('document_id', 35),
                             ('current_source', False), ('all_parts_current', False)):
            with self.subTest(field=field):
                stale = dict(self.state, **{field: value})
                self.assertFalse(source_matches(stale, self.metadata, 21, 34))

    def test_old_fixture_metadata_cannot_match(self):
        old_fixture = dict(self.metadata, name='Garden preview', size=[32, 12, 32], blocks=800)
        self.assertFalse(source_matches(self.state, old_fixture, 21, 34))

    def test_remote_probe_snippets_compile_after_formatting(self):
        snippets = (INSTALL_PROBE, STATUS, RESTORE, CELL_ROIS,
                    LOAD % ('fern', 5, 'covered'))
        for index, snippet in enumerate(snippets):
            with self.subTest(index=index):
                compile(snippet, '<live-qa-snippet-%d>' % index, 'exec')

    def test_current_cached_model_is_allowed_but_stale_renderer_is_not(self):
        self.assertTrue(editor_preview_ready(self.state, self.metadata, 21, 34))
        for field, value in (('renderer_age', .8), ('renderer_active', False),
                             ('model_revision_current', False), ('model_name', None)):
            with self.subTest(field=field):
                state = dict(self.state, **{field: value})
                self.assertFalse(editor_preview_ready(state, self.metadata, 21, 34))
        state = dict(self.state, parts=[{'pending': False, 'cache_current': False, 'name': 'old_model'}])
        self.assertFalse(editor_preview_ready(state, self.metadata, 21, 34))

    def test_empty_document_cannot_accept_previous_fixture_model(self):
        metadata = dict(self.metadata, blocks=0)
        state = dict(self.state, metadata=metadata, model_name=None, parts=[], renderer_active=False)
        self.assertTrue(editor_preview_ready(state, metadata, 21, 34))
        state['model_name'] = 'previous_fixture'
        self.assertFalse(editor_preview_ready(state, metadata, 21, 34))

    def test_failed_native_submission_and_pending_mount_are_rejected(self):
        state = dict(self.state, native_calls=[{'result': False, 'error': 'native failure'}])
        self.assertFalse(editor_preview_ready(state, self.metadata, 21, 34))
        state = dict(self.state, parts=[{'pending': True, 'cache_current': True, 'name': 'warming_model'}])
        self.assertFalse(editor_preview_ready(state, self.metadata, 21, 34))

    def test_liquid_plans_and_native_controls_must_both_be_current_when_enabled(self):
        liquid = {'enabled': True, 'owned': True, 'plan_ready': True,
                  'controls_pending': False, 'groups': 2, 'error': ''}
        self.assertTrue(editor_preview_ready(dict(self.state, liquid=liquid), self.metadata, 21, 34))
        for field, value in (('owned', False), ('plan_ready', False), ('controls_pending', True)):
            with self.subTest(field=field):
                state = dict(self.state, liquid=dict(liquid, **{field: value}))
                self.assertFalse(editor_preview_ready(state, self.metadata, 21, 34))
        state = dict(self.state, liquid=dict(liquid, error='Liquid model ID did not become ready'))
        with self.assertRaisesRegex(AssertionError, 'liquid preview failed'):
            editor_preview_ready(state, self.metadata, 21, 34)

    def test_empty_liquid_plan_still_requires_owner_after_water_removal(self):
        metadata = dict(self.metadata, blocks=0)
        liquid = {'enabled': True, 'owned': True, 'plan_ready': True,
                  'controls_pending': False, 'groups': 0, 'error': ''}
        state = dict(self.state, metadata=metadata, model_name=None, parts=[],
                     renderer_active=False, liquid=liquid)
        self.assertTrue(editor_preview_ready(state, metadata, 21, 34))
        liquid['plan_ready'] = False
        self.assertFalse(editor_preview_ready(state, metadata, 21, 34))


if __name__ == '__main__':
    unittest.main()
