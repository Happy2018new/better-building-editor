"""Prospective pixel gates reject absence, frozen glint and background motion."""
import copy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import analyze_item_sprite_product as analyzer
from analyze_item_sprite_product import (analyze, body_measurement, expected_mask, item_polygons,
                                         temporal_measurement, point_sampled_mask)
from item_sprite_capture_contract import (camera_matches, paired_layout_matches,
                                          scene_layout, snapshot_digest)
from analyze_item_sprite_closeup import elapsed_sequence
from projection.camera import OrbitCamera
from projection.debug_blueprints import build
from projection.debug_item_blueprints import IDENTITY, PAIRS
from projection.item_sprite_plan import iter_render_steps
from projection.item_sprite_profile import candidate_profile
from projection.liquid_viewport import group_view


class ItemPixelTests(unittest.TestCase):
    def setUp(self):
        self.mask = np.zeros((32, 32), dtype=bool)
        self.mask[10:14, 10:14] = True
        self.mask[14:18, 14:18] = True
        self.baseline = np.zeros((32, 32, 3), dtype=np.int16)
        self.body = self.baseline.copy()
        self.body[self.mask] = (25, 70, 100)

    def test_declared_body_must_exist_at_its_silhouette_and_not_merely_nearby(self):
        self.assertTrue(body_measurement(self.body, self.baseline, self.mask)['passed'])
        self.assertFalse(body_measurement(self.baseline, self.baseline, self.mask)['passed'])
        shifted = np.roll(self.body, 3, axis=1)
        self.assertFalse(body_measurement(shifted, self.baseline, self.mask)['passed'])
        extra = self.body.copy()
        extra[10:18, 10:18] = (25, 70, 100)
        self.assertFalse(body_measurement(extra, self.baseline, self.mask)['passed'])

    def test_only_enchanted_content_may_animate_and_the_highlight_must_stay_in_the_body(self):
        moving = self.body.copy()
        moving[self.mask] += (15, 6, 24)
        images = [self.body, moving, self.body]
        self.assertTrue(temporal_measurement(images, self.mask, True)['passed'])
        self.assertFalse(temporal_measurement(images, self.mask, False)['passed'])
        self.assertTrue(temporal_measurement([self.body]*3, self.mask, False)['passed'])
        self.assertFalse(temporal_measurement([self.body]*3, self.mask, True)['passed'])
        background = moving.copy()
        background[6:22, 6:22] += 10
        self.assertFalse(temporal_measurement([self.body, background, self.body], self.mask, True)['passed'])

    def test_opaque_bitmap_pixels_and_all_faces_have_finite_declared_planes(self):
        image = Image.new('RGBA', (2, 2))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.putpixel((1, 0), (0, 255, 0, 127))
        pose = {'size_pixels': 8., 'front_z_pixels': 15.}
        for facing in range(6):
            for rotation in range(0, 360, 45):
                polygons = list(item_polygons((3, 2, 1), image, pose, rotation, facing))
                self.assertEqual(1, len(polygons))
                self.assertTrue(all(np.isfinite(point).all() for point in polygons[0]))
                self.assertTrue(all(0 <= point[axis]-(3, 2, 1)[axis] <= 1
                                    for point in polygons[0] for axis in range(3)))

    def test_pixel_centers_sample_checker_texels_without_inclusive_edge_growth(self):
        texture = Image.new('RGBA', (2, 2))
        texture.putpixel((0, 0), (255, 255, 255, 255))
        texture.putpixel((1, 1), (255, 255, 255, 255))
        mask = point_sampled_mask(texture, ((10, 10), (14, 10), (14, 14), (10, 14)), (24, 24))
        expected = np.zeros((24, 24), dtype=bool)
        expected[10:12, 10:12] = True
        expected[12:14, 12:14] = True
        np.testing.assert_array_equal(expected, mask)

    def test_failed_startup_or_no_capture_never_qualifies_any_visual_gate(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)/'failure.json'
            path.write_text(json.dumps({'schema': 2, 'completed': False, 'captures': [],
                'cleanup_errors': [], 'production_qualified': False}), encoding='ascii')
            result = analyze(path)
        self.assertFalse(result['evidence_valid'])
        self.assertFalse(result['production_qualified'])
        self.assertFalse(result['native_glint_accepted'])
        self.assertEqual({}, result['observed_product_gates'])

    def test_complete_synthetic_capture_replays_all_controls_but_never_promotes_production(self):
        document, profile = build(IDENTITY), candidate_profile()
        size = (640, 480)
        camera = OrbitCamera(180., 20., 1.6)
        state = {'camera_pose': [180., 20., 1.6], 'camera_pan': [0., 0.], 'camera_depth': 0.,
                 'screen_size': list(size), 'groups_data': [], 'banks': []}
        for index, group in enumerate(row for row in iter_render_steps(document, profile) if row is not None):
            view = group_view(group.origin, camera, (0, 0, 0), document.size, size, 20.)
            position = [view.position[i]+profile.ui_offset(view.size)[i] for i in range(2)]
            pose = list(profile.ui_pose(20., 20., 180., view.size))
            state['groups_data'].append({'key': repr(group.key), 'origin': list(group.origin)})
            state['banks'].append({'key': repr(group.key), 'front': 0, 'ids': [index*2+1, index*2+2],
                'poses': [pose, pose], 'doll_positions': [position, position],
                'doll_sizes': [list(view.size), list(view.size)], 'visible': [True, False]})
        spec_path = analyzer.source_path()
        spec = json.loads(spec_path.read_bytes())
        texture_path = ROOT/spec['items'][0]['generated_texture']
        inputs = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (spec_path, texture_path)}
        yy, xx = np.indices((size[1], size[0]))
        background = np.repeat(((xx+yy) % 2 * 20+20)[:, :, None], 3, axis=2).astype(np.uint8)
        frames = [background.copy() for unused in range(3)]
        first = {'label': 'editor_temporal_0', 'state': state}
        with Image.open(texture_path) as texture:
            for pair in PAIRS:
                for mode in ('plain', 'enchanted'):
                    selected = expected_mask(pair[mode], first, texture, spec['frame_pose'], size)
                    for index in range(3):
                        frames[index][selected] = (25+index*10 if mode == 'enchanted' else 25,
                                                   100, 170+index*15 if mode == 'enchanted' else 170)
        binding = {'owner': 'synthetic-unit-control', 'game_pid': 123, 'game_identity': 'fixture',
                   'session_file': 'synthetic-unit-control.json'}
        report = {'schema': 2, 'fixture': IDENTITY, 'completed': True, 'cleanup_errors': [],
                  'session': binding, 'launch_inputs': inputs, 'inputs_after': inputs,
                  'launch_inputs_sha256': snapshot_digest(inputs), 'source_unchanged': True, 'captures': []}
        with TemporaryDirectory() as directory:
            root = Path(directory)
            for index, pixels in enumerate(frames+[background]):
                label = 'editor_temporal_'+str(index) if index < 3 else 'editor_items_hidden'
                image = root/(label+'.png')
                Image.fromarray(pixels).save(image)
                captured_state = copy.deepcopy(state)
                if index == 3:
                    for bank in captured_state['banks']:
                        bank['visible'] = [False, False]
                report['captures'].append({'label': label, 'state': captured_state, 'state_after': copy.deepcopy(captured_state),
                    'capture': dict(binding, ok=True, reliable=True, background_only=True,
                        background_safe=True, native_resolution=True, backend='Windows.Graphics.Capture',
                        frame={'backend': 'Windows.Graphics.Capture', 'request_qpc_100ns': index*2,
                               'frame_qpc_100ns': index*2+1}, variance=[100., 100., 100.], path=str(image),
                        width=size[0], height=size[1], sha256=hashlib.sha256(image.read_bytes()).hexdigest())})
            path = root/'report.json'
            path.write_text(json.dumps(report), encoding='ascii')
            with patch.object(analyzer, 'snapshot_sources', return_value=inputs):
                result = analyze(path)
                self.assertTrue(result['evidence_valid'])
                self.assertTrue(result['observed_product_gates']['editor']['body'])
                self.assertTrue(result['observed_product_gates']['editor']['animation'])
                self.assertFalse(result['production_qualified'])
                report['captures'][1]['state_after']['banks'][0]['poses'][0][0] += .01
                path.write_text(json.dumps(report), encoding='ascii')
                self.assertFalse(analyze(path)['evidence_valid'])


class ItemCaptureContracts(unittest.TestCase):
    def test_animation_duration_uses_native_frame_clock_and_rejects_duplicate_or_short_sequences(self):
        def sequence(times):
            return [{'capture': {'frame': {'frame_qpc_100ns': int(value*10000000)}}} for value in times]
        self.assertTrue(elapsed_sequence(sequence([100., 102., 104., 107.]))['passed'])
        self.assertFalse(elapsed_sequence(sequence([100., 100., 107.]))['passed'])
        self.assertFalse(elapsed_sequence(sequence([100., 103., 106.]))['passed'])

    def scene(self):
        return {'camera_pose': [180., 20., 1.6], 'camera_pan': [0., 0.],
                'camera_depth': 0., 'screen_size': [1200., 800.], 'banks': [
                    {'key': 'first', 'front': 0, 'ids': [10, 11],
                     'poses': [[.1, -70., 0., 180.], [.1, -70., 0., 180.]],
                     'doll_positions': [[0., 0.], [0., 0.]],
                     'doll_sizes': [[1200., 800.], [1200., 800.]],
                     'visible': [True, False]}]}

    def test_muting_keeps_native_pose_while_position_or_model_changes_invalidate_pairs(self):
        first, second = self.scene(), self.scene()
        second['banks'][0]['visible'] = [False, False]
        self.assertTrue(paired_layout_matches(first, second))
        second['banks'][0]['doll_positions'][0][0] += 1.
        self.assertFalse(paired_layout_matches(first, second))
        second = self.scene()
        second['banks'][0]['ids'][0] = None
        self.assertIsNone(scene_layout(second))
        second = self.scene()
        second['banks'][0]['doll_sizes'][0][0] = 0.
        self.assertIsNone(scene_layout(second))

    def test_camera_viewport_orientation_and_finite_values_are_required(self):
        first = {'position': [0., 4., -28.], 'rotation': [10., 180., 0.],
                 'screen': [1200, 800], 'fov': 70.}
        self.assertTrue(camera_matches(first, copy.deepcopy(first)))
        for key, value in (('screen', [1280, 800]), ('rotation', [10., 181., 0.]),
                           ('position', [1., 4., -28.]), ('fov', float('nan'))):
            second = dict(first, **{key: value})
            self.assertFalse(camera_matches(first, second))
        self.assertFalse(camera_matches(None, first))

    def test_source_contract_is_order_independent_but_content_sensitive(self):
        self.assertEqual(snapshot_digest({'a': '1', 'b': '2'}), snapshot_digest({'b': '2', 'a': '1'}))
        self.assertNotEqual(snapshot_digest({'a': '1'}), snapshot_digest({'a': '2'}))


if __name__ == '__main__':
    unittest.main()
