"""Product pixel observations must reject missing, stale and opaque controls."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_product_water import analyze, contribution, product_geometry
from water_capture_contract import camera_matches


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


if __name__ == '__main__':
    unittest.main()
