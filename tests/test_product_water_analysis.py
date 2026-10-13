"""Product pixel observations must reject missing, stale and opaque controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_product_water import analyze, contribution, product_geometry
from water_capture_contract import (camera_matches, calibrated_viewport_matches, scene_capture_state,
                                    stable_scene_predicate)


class ProductWaterAnalysisTests(unittest.TestCase):
    def evidence(self, directory):
        path = Path(directory) / 'frame.png'
        image = Image.new('RGB', (32, 32), (30, 40, 50))
        image.putpixel((0, 0), (200, 200, 200))
        image.save(path)
        binding = {'owner': 'owned', 'game_pid': 9, 'game_identity': '123', 'session_file': 'session.json'}
        capture = dict(binding, ok=True, reliable=True, background_only=True, background_safe=True,
                       native_resolution=True, backend='Windows.Graphics.Capture', variance=[30., 30., 30.],
                       width=32, height=32, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                       frame={'backend': 'Windows.Graphics.Capture', 'request_qpc_100ns': 100, 'frame_qpc_100ns': 101})
        sources = {'behavior_pack/example.py': '1' * 64, 'resource_pack/example.vertex': '2' * 64}
        return {'completed': True, 'restored': True, 'cleanup_errors': [], 'captures': {'frame': capture},
                'rows': {}, 'session_binding': binding, 'frozen': True, 'source_unchanged': True,
                'launch_source_sha256': sources.copy(), 'source_file_sha256_before': sources.copy(),
                'source_file_sha256_after': sources.copy(),
                'source_contract_sha256': hashlib.sha256(
                    json.dumps(sources, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()}

    def replay(self, directory, source):
        path = Path(directory) / 'source.json'
        path.write_text(json.dumps(source), encoding='ascii')
        return analyze(path)

    def assert_rejected(self, result):
        self.assertFalse(result['evidence_valid'])
        self.assertFalse(any(result['observed_product_gates'].values()))
        self.assertFalse(result['product_style_accepted'])

    def test_empty_capture_report_remains_a_replayable_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.evidence(directory)
            source['captures'].clear()
            self.assert_rejected(self.replay(directory, source))

    def test_capture_provenance_and_runtime_restore_are_required_before_pixels(self):
        with tempfile.TemporaryDirectory() as directory:
            original = self.evidence(directory)
            for field, value in (('reliable', False), ('background_safe', False), ('owner', 'other'),
                                 ('game_identity', '124'), ('sha256', '0' * 64)):
                source = deepcopy(original)
                source['captures']['frame'][field] = value
                with self.subTest(field=field):
                    self.assert_rejected(self.replay(directory, source))
            for field, value in (('completed', False), ('restored', False), ('cleanup_errors', ['world restore failed'])):
                source = deepcopy(original)
                source[field] = value
                with self.subTest(field=field):
                    self.assert_rejected(self.replay(directory, source))

    def test_absent_requested_route_and_control_cannot_disappear_from_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.evidence(directory)
            source.update(routes=['editor', 'missing'], cases=['source'], controls=['wet', 'dry'])
            result = self.replay(directory, source)
            self.assert_rejected(result)
            self.assertEqual(4, len(result['capture_failures']))

    def test_missing_row_capture_cannot_be_measured_as_another_control(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.evidence(directory)
            source['rows']['editor_source_wet'] = {'control': 'wet'}
            self.assert_rejected(self.replay(directory, source))

    def test_source_resource_drift_and_wrong_launch_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            original = self.evidence(directory)
            for field in ('source_file_sha256_after', 'launch_source_sha256'):
                source = deepcopy(original)
                source[field]['resource_pack/example.vertex'] = '3' * 64
                with self.subTest(field=field):
                    self.assert_rejected(self.replay(directory, source))
            for field, value in (('source_unchanged', False), ('source_contract_sha256', '0' * 64)):
                source = deepcopy(original)
                source[field] = value
                with self.subTest(field=field):
                    self.assert_rejected(self.replay(directory, source))

    def test_world_camera_and_paired_control_drift_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            source = self.evidence(directory)
            pose = {'position': [0., 0., 12.], 'rotation': [0., 0., 0.], 'screen': [32, 32], 'fov': 60.}
            source['camera_calibration'] = {'engine_screen': [32, 32], 'reported_fov': 60., 'capture_size': [32, 32]}
            for label, control in (('full_source_wet', 'wet'), ('full_source_dry', 'dry')):
                source['captures'][label] = dict(source['captures']['frame'],
                    camera_expected=deepcopy(pose), camera_before=deepcopy(pose), camera_after=deepcopy(pose))
                source['rows'][label] = dict(route='full', case='source', control=control,
                    camera_expected=deepcopy(pose), camera=deepcopy(pose),
                    camera_before=deepcopy(pose), camera_after=deepcopy(pose))
            source['rows']['full_source_dry']['camera']['position'][0] += 1.
            self.assert_rejected(self.replay(directory, source))
            source['rows']['full_source_dry']['camera'] = deepcopy(pose)
            source['captures']['full_source_wet']['camera_after']['rotation'][1] += 1.
            self.assert_rejected(self.replay(directory, source))

    def test_camera_fov_and_viewport_drift_are_not_position_equivalence(self):
        pose = {'position': [0., 0., 12.], 'rotation': [0., 0., 0.], 'screen': [32, 32], 'fov': 60.}
        self.assertTrue(camera_matches(pose, pose))
        for field, value in (('screen', [64, 64]), ('fov', 61.)):
            with self.subTest(field=field):
                self.assertFalse(camera_matches(pose, dict(pose, **{field: value})))

    def test_engine_ui_units_are_independent_from_physical_capture_pixels(self):
        pose = {'position': [0., 0., 12.], 'rotation': [0., 0., 0.], 'screen': [499., 277.], 'fov': 60.}
        calibration = {'engine_screen': [499., 277.], 'capture_size': [1994, 1105], 'reported_fov': 60.}
        self.assertTrue(calibrated_viewport_matches(pose, calibration))
        self.assertFalse(calibrated_viewport_matches(dict(pose, screen=[1994, 1105]), calibration))

    def scene_state(self):
        return {'camera_pose': [35., 25., 4.6], 'camera_pan': [0., 0.], 'camera_depth': 0.,
                'depth_plane': None, 'scene_origin': [0, 0, 0], 'scene_size': [10, 8, 10],
                'screen_size': [499., 277.], 'backend_ready': True,
                'liquid_control_requests': [{'key': 'water', 'geometry': [[0., 0.], [300., 120.]],
                    'visible': [True], 'poses': [[.32, -65., 0., 35.]],
                    'doll_positions': [[58., 121.]], 'doll_sizes': [[300., 120.]]}]}

    def test_scene_settlement_waits_for_exact_target_then_native_layout_stability(self):
        accept = stable_scene_predicate((35., 25., 4.6), (0., 0.), lambda state: state['backend_ready'])
        moving = self.scene_state()
        moving['camera_pose'][2] = 4.599760046768113
        self.assertFalse(accept(moving))
        self.assertFalse(accept(deepcopy(moving)))
        self.assertFalse(accept(self.scene_state()))
        self.assertTrue(accept(self.scene_state()))

    def test_scene_settlement_rejects_native_layout_drift_and_resets_after_pending(self):
        accept = stable_scene_predicate((35., 25., 4.6), (0., 0.), lambda state: state['backend_ready'])
        self.assertFalse(accept(self.scene_state()))
        moved = self.scene_state()
        moved['liquid_control_requests'][0]['doll_positions'][0][0] += .001
        self.assertFalse(accept(deepcopy(moved)))
        self.assertTrue(accept(deepcopy(moved)))
        pending = deepcopy(moved)
        pending['backend_ready'] = False
        self.assertFalse(accept(pending))
        self.assertFalse(accept(deepcopy(moved)))
        self.assertTrue(accept(deepcopy(moved)))

    def test_scene_settlement_cannot_accept_wrong_requested_pose_or_pan(self):
        for field, axis in (('camera_pose', 0), ('camera_pose', 1), ('camera_pose', 2), ('camera_pan', 0)):
            with self.subTest(field=field, axis=axis):
                accept = stable_scene_predicate((35., 25., 4.6), (0., 0.), lambda state: state['backend_ready'])
                wrong = self.scene_state()
                wrong[field][axis] += .00001
                self.assertFalse(accept(deepcopy(wrong)))
                self.assertFalse(accept(deepcopy(wrong)))

    def test_blank_and_wrong_water_silhouettes_fail_even_when_in_the_roi(self):
        expected = np.zeros((64, 64), dtype=bool)
        expected[20:40, 20:40] = True
        self.assertTrue(product_geometry(expected, expected)['passed'])
        self.assertFalse(product_geometry(np.zeros_like(expected), expected)['passed'])
        wrong = np.zeros_like(expected)
        wrong[30:50, 20:40] = True
        self.assertFalse(product_geometry(wrong, expected)['passed'])

    def test_opaque_water_and_missing_underlying_region_fail_contribution(self):
        water = np.zeros((32, 32, 3), dtype=np.int16)
        water[8:24, 8:24] = (20, 40, 70)
        body = np.zeros((32, 32), dtype=bool)
        body[10:20, 12:16] = True
        self.assertFalse(contribution(water, water.copy(), body)['passed'])
        transparent = water.copy()
        transparent[body] = (80, 60, 60)
        self.assertTrue(contribution(transparent, water, body)['passed'])
        self.assertFalse(contribution(transparent, water, np.zeros_like(body))['passed'])

    def test_animation_uses_its_declared_threshold_independently_of_geometry(self):
        first = np.zeros((32, 32, 3), dtype=np.int16)
        later = first.copy()
        later[10:20, 12:16] = 5
        selected = np.zeros((32, 32), dtype=bool)
        selected[10:20, 12:16] = True
        self.assertFalse(contribution(first, later, selected)['passed'])
        self.assertTrue(contribution(first, later, selected, threshold=2)['passed'])

    def transparency_evidence(self, directory, opaque=False):
        source = self.evidence(directory)
        controls = ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty')
        source.update(routes=['editor'], cases=['wet_oak_fence'], controls=controls)
        body = np.zeros((32, 32), dtype=bool)
        body[10:20, 10:14] = True
        rear = np.zeros_like(body)
        rear[10:20, 20:24] = True
        ready = {'camera_pose': [0., 0., 3.], 'camera_pan': [0., 0.], 'camera_depth': 0., 'depth_plane': None,
                 'scene_origin': [0, 0, 0], 'scene_size': [10, 8, 10], 'screen_size': [32, 32],
                 'liquid_control_requests': []}
        for control in controls:
            pixels = np.zeros((32, 32, 3), dtype=np.uint8)
            pixels[0, 0] = 200
            if control != 'empty':
                pixels[body | rear] = (20, 40, 70)
            if control == 'dry':
                pixels[body | rear] = (150, 100, 50)
            elif control == 'wet' and not opaque:
                pixels[body] = (80, 60, 60)
                pixels[rear] = (90, 70, 40)
            elif control == 'liquid_only':
                pixels[rear] = (90, 70, 40)
            elif control == 'rearless':
                pixels[body] = (80, 60, 60)
            label = 'editor_wet_oak_fence_' + control
            path = Path(directory) / (label + '.png')
            Image.fromarray(pixels).save(path)
            row = dict(route='editor', case='wet_oak_fence', control=control, ready=deepcopy(ready),
                       scene_before=scene_capture_state(ready), scene_after=scene_capture_state(ready))
            source['rows'][label] = row
            source['captures'][label] = dict(source['captures']['frame'], path=str(path),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                scene_before=deepcopy(row['scene_before']), scene_after=deepcopy(row['scene_after']))
        return source, body, rear

    def replay_transparency(self, directory, source, body, rear):
        def region(unused_row, unused_source, unused_size, points):
            return body if points[0][0] > 3.4 else rear
        with patch('analyze_product_water.expected_mask', return_value=body | rear), \
                patch('analyze_product_water.region_mask', side_effect=region):
            return self.replay(directory, source)

    def test_full_replay_transparency_uses_all_independent_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            source, body, rear = self.transparency_evidence(directory)
            result = self.replay_transparency(directory, source, body, rear)
            self.assertTrue(result['evidence_valid'])
            self.assertTrue(result['observed_product_gates']['transparency'])
            opaque, body, rear = self.transparency_evidence(directory, opaque=True)
            self.assertFalse(self.replay_transparency(directory, opaque, body, rear)['observed_product_gates']['transparency'])

    def test_individually_stable_transparency_controls_must_share_one_scene_pose(self):
        with tempfile.TemporaryDirectory() as directory:
            source, body, rear = self.transparency_evidence(directory)
            label = 'editor_wet_oak_fence_liquid_only'
            row = source['rows'][label]
            row['ready']['camera_pan'][0] = 1.
            row['scene_before'] = scene_capture_state(row['ready'])
            row['scene_after'] = deepcopy(row['scene_before'])
            source['captures'][label]['scene_before'] = deepcopy(row['scene_before'])
            source['captures'][label]['scene_after'] = deepcopy(row['scene_after'])
            result = self.replay_transparency(directory, source, body, rear)
            self.assert_rejected(result)
            self.assertIn({'paired_scene_pose_drift': label}, result['capture_failures'])


if __name__ == '__main__':
    unittest.main()
