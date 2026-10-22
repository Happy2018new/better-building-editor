"""Explicit SDK GUI coordinates preserve legacy readings and reject bad caches."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_product_water as product
import analyze_product_water_biome as biome
import analyze_product_water_flow as flow
import analyze_water_acceptance_r16 as acceptance
import qualify_water_product_r16 as qualifier
from tests import test_product_water_analysis as analysis_fixtures
from water_capture_contract import scene_capture_state


def recorded_pool_state():
    # R28 pool native observation: these are actual Doll global geometry and pose.
    return {'camera_pose': [35., 25., 4.6], 'screen_size': [641., 360.],
            'gui_cache': {'sdk_integer_gui': 2., 'cached_gui': 2.},
            'liquid_groups': [{'key': 'water', 'origin': [0, 0, 0]}],
            'liquid_control_requests': [{'key': 'water', 'visible': [False, True],
                'doll_positions': [[75.0407485961914, 115.875]] * 2,
                'doll_sizes': [[418.5842590332031, 583.2905883789062]] * 2,
                'poses': [None, [.1264003591347252, -65., 0., 35.]]}]}


class WaterEditorGuiAnalysisTests(unittest.TestCase):
    def test_legacy_project_keeps_three_argument_coordinate_adapter_compatible(self):
        row = {'route': 'editor', 'ready': {'screen_size': [100., 100.]}}
        points, shape = [(1., 2., 3.)], {'position': [0, 0, 0]}

        def original_callback(actual_points, actual_shape, state):
            self.assertIs(points, actual_points)
            self.assertIs(shape, actual_shape)
            self.assertIs(row['ready'], state)
            return [(10., 20.)]

        with patch.object(product, 'scene_project', side_effect=original_callback):
            self.assertEqual([(20., 40.)], product.project(points, shape, row, {}, (200, 200)))

    def test_five_frozen_old_A_default_readings_are_exactly_unchanged(self):
        path = ROOT / 'tests/data/water_editor_legacy_gui4_readings_v1.json'
        fixtures = json.loads(path.read_bytes())
        self.assertEqual(5, len(fixtures['rows']))
        for row in fixtures['rows']:
            expected = [tuple(point) for point in row['expected_legacy_gui4_points']]
            self.assertEqual(expected, product.scene_project(row['points'], row['shape'], row['state']))
            self.assertEqual(expected, product.scene_project(row['points'], row['shape'], row['state'], native_gui=4.))
            # Even a malformed cache cannot silently change the legacy mode.
            state = dict(row['state'], gui_cache={'sdk_integer_gui': 'invalid'})
            self.assertEqual(expected, product.scene_project(row['points'], row['shape'], state))

    def test_recorded_pool_anchor_uses_actual_GUI2_and_legacy_is_a_negative_control(self):
        state, shape, points = recorded_pool_state(), {'position': [3, 3, 3]}, [(2., 2., 2.)]
        expected = (284.33287811279297, 198.22816467285156)
        actual = product.scene_project(points, shape, state, native_gui=2.)[0]
        self.assertEqual(expected, actual)
        old = product.scene_project(points, shape, state)[0]
        self.assertAlmostEqual(104.64606475830078, old[1] - actual[1])
        self.assertNotEqual(old, actual)
        for gui in (None, True, False, '2', 0, -1, .5, 2.5, float('nan'), float('inf')):
            with self.subTest(gui=gui), self.assertRaises(ValueError):
                product.scene_project(points, shape, state, native_gui=gui)

    def test_raw_JSON_fields_do_not_enable_or_override_explicit_GUI_mode(self):
        state = recorded_pool_state()
        row = {'route': 'editor', 'ready': state}
        shape, points, size = {'position': [3, 3, 3]}, [(2., 2., 2.)], (1280, 720)
        source = {'rows': {'editor_pool_wet': row}, '_native_editor_gui': True,
                  'native_editor_gui': True, 'editor_geometry_oracle': {'native_gui': 1.}}
        legacy = product.project(points, shape, row, source, size)
        self.assertEqual([(284.33287811279297 * 1280 / 641., 302.87422943115234 * 2.)], legacy)
        oracle = product.bind_native_editor_gui(source)
        self.assertEqual([2.], oracle['native_gui_scales'])
        self.assertEqual(1, oracle['states_verified'])
        self.assertEqual([(284.33287811279297 * 1280 / 641., 198.22816467285156 * 2.)],
                         product.project(points, shape, row, source, size))

    def test_invalid_SDK_cache_and_extra_alpha_or_burst_state_are_rejected(self):
        for cache in (None, {}, {'sdk_integer_gui': 2., 'cached_gui': 3.},
                      {'sdk_integer_gui': True, 'cached_gui': True},
                      {'sdk_integer_gui': 1., 'cached_gui': True},
                      {'sdk_integer_gui': float('nan'), 'cached_gui': float('nan')},
                      {'sdk_integer_gui': 2.5, 'cached_gui': 2.5}):
            state = dict(recorded_pool_state(), gui_cache=cache)
            source = {'rows': {'editor_pool_wet': {'ready': state}}}
            with self.subTest(cache=cache), self.assertRaises(ValueError):
                product.bind_native_editor_gui(source)
            self.assertNotIn(product._NATIVE_EDITOR_GUI, source)
        valid, invalid = recorded_pool_state(), recorded_pool_state()
        invalid['gui_cache']['cached_gui'] = 3.
        additions = (
            {'extra_rows': {'editor_pool_wet_section': {'ready': invalid}}},
            {'alpha_controls': {'editor_pool_wet': {'baseline': valid,
                                                    'phases': {'1': {'ready': invalid}}}}},
            {'flow_bursts': {'flow': {'row': {'route': 'editor', 'ready': invalid}}}})
        for extra in additions:
            source = dict({'rows': {'editor_pool_wet': {'ready': valid}}}, **extra)
            with self.subTest(extra=list(extra)), self.assertRaises(ValueError):
                product.bind_native_editor_gui(source)
            self.assertNotIn(product._NATIVE_EDITOR_GUI, source)

    def dry_report(self, directory):
        fixtures = analysis_fixtures.ProductWaterAnalysisTests()
        source, state = fixtures.evidence(directory), fixtures.scene_state()
        state['gui_cache'] = {'sdk_integer_gui': 2., 'cached_gui': 2.}
        label = 'editor_source_dry'
        layout = scene_capture_state(state)
        source['rows'][label] = {'route': 'editor', 'case': 'source', 'control': 'dry',
                                'ready': state, 'scene_before': layout, 'scene_after': deepcopy(layout)}
        source['captures'][label] = dict(source['captures']['frame'],
                                        scene_before=layout, scene_after=deepcopy(layout))
        source['routes'] = ['editor']
        path = Path(directory) / 'source.json'
        path.write_text(json.dumps(source), encoding='ascii')
        return path, source

    def test_invalid_explicit_GUI_rejects_evidence_before_any_pixel_region(self):
        with tempfile.TemporaryDirectory() as directory:
            path, source = self.dry_report(directory)
            source['rows']['editor_source_dry']['ready']['gui_cache']['cached_gui'] = 3.
            path.write_text(json.dumps(source), encoding='ascii')
            original = path.read_bytes()
            self.assertTrue(product.analyze(path)['evidence_valid'])
            with patch.object(product, 'expected_mask', side_effect=AssertionError('Must not sample pixels')):
                measured = product.analyze(path, native_editor_gui=True)
            self.assertFalse(measured['evidence_valid'])
            self.assertIsNone(measured['editor_geometry_oracle'])
            self.assertIn('native_editor_gui', measured['capture_failures'][0])
            self.assertEqual(original, path.read_bytes())

    def test_side_and_qualifier_receive_the_same_validated_mode_without_report_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path, unused = self.dry_report(directory)
            original = path.read_bytes()
            measured = acceptance.replay(path, native_editor_gui=True)
            self.assertTrue(measured['evidence_valid'])
            self.assertEqual([2.], measured['editor_geometry_oracle']['native_gui_scales'])
            report, measured = qualifier.analyze_report(path, native_editor_gui=True)
            self.assertTrue(measured['evidence_valid'])
            self.assertIs(True, report[product._NATIVE_EDITOR_GUI])
            self.assertEqual('captured_paperdoll_layout_with_sdk_integer_gui',
                             qualifier.analysis_oracles(report, native_editor_gui=True)['editor_masks'])
            legacy, unused = qualifier.analyze_report(path)
            self.assertNotIn(product._NATIVE_EDITOR_GUI, legacy)
            self.assertEqual(original, path.read_bytes())

    def test_flow_and_biome_do_not_fall_back_after_invalid_explicit_GUI(self):
        with tempfile.TemporaryDirectory() as directory:
            path, source = self.dry_report(directory)
            del source['rows']['editor_source_dry']['ready']['gui_cache']
            path.write_text(json.dumps(source), encoding='ascii')
            for analyze in (flow.analyze_flow, biome.biome_analysis):
                with self.subTest(analyzer=analyze.__name__):
                    result = analyze(path, native_editor_gui=True)
                    self.assertFalse(result['evidence_valid'])
                    self.assertFalse(result['passed'])
                    self.assertIn('native_editor_gui', result['capture_failures'][0])


if __name__ == '__main__':
    unittest.main()
