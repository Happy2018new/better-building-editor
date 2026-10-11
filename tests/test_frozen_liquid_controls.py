"""Public-source and layer-drift gates; no native pixels are accepted here."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import capture_frozen_liquid_controls as frozen
import record_contained_liquid_heights as recorder
from projection.cell import AIR, encode
from test_pure_liquid_native_controls import snapshot


class FrozenLiquidControlTests(unittest.TestCase):
    def test_empty_shell_cleanup_does_not_request_empty_native_snapshot(self):
        harness = object.__new__(frozen.FrozenHarness)
        with patch.object(frozen.contained.NativeHarness, 'clear') as native_clear:
            self.assertEqual({'writes': [], 'empty_positions': True, 'no_native_call': True},
                             harness.clear([]))
            native_clear.assert_not_called()

    def test_flow_restore_preserves_preexisting_owner_and_handles_unstarted_freeze(self):
        from types import SimpleNamespace
        import json
        calls = []
        game = SimpleNamespace(ForbidLiquidFlow=lambda value: calls.append(value) or True)
        api = SimpleNamespace(GetLevelId=lambda: 'level',
                              GetEngineCompFactory=lambda: SimpleNamespace(CreateGame=lambda unused: game))
        for initial in (None, 'owned', 'other'):
            state = SimpleNamespace()
            if initial is not None:
                state._frozen_liquid_flow_owner = initial
            environment = dict(sys=state, api=api, json=json)
            calls[:] = []
            if initial == 'other':
                with self.assertRaises(AssertionError):
                    exec(frozen.FLOW_RESTORE % 'owned', environment)
                self.assertEqual('other', state._frozen_liquid_flow_owner)
            else:
                exec(frozen.FLOW_RESTORE % 'owned', environment)
                self.assertFalse(hasattr(state, '_frozen_liquid_flow_owner'))
            self.assertEqual([False] if initial == 'owned' else [], calls)

    def test_all_public_cases_preserve_exact_control_layers_and_neighbors(self):
        origin, platform = (8, 110, -3), (-10, 105, -20)
        for identity in frozen.CASE_IDS:
            with self.subTest(identity=identity):
                plan = frozen.fixture_plan(identity, origin, platform)
                self.assertFalse(plan['context_changed'])
                self.assertEqual([], plan['shell'])
                for control in frozen.contained.CONTROLS:
                    public = frozen.source_document(identity, isolated=True, control=control)
                    expected = [
                        (tuple(plan['document_origin'][i] + pos[i] for i in range(3)), encode(value))
                        for pos, value in sorted(public.blocks.items())]
                    self.assertEqual(expected, plan['controls'][control]['cells'])
                    self.assertTrue(set(pos for pos, unused in expected).issubset(plan['cavity']))
                self.assertIn(platform, plan['reserved'])
                self.assertNotIn(platform, plan['cavity'])

    def test_platform_overlap_is_rejected_before_native_work(self):
        with self.assertRaisesRegex(ValueError, 'overlaps'):
            frozen.fixture_plan('water_depth_0_foreground', (8, 110, -3), (8, 110, -3))

    def test_unknown_case_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown'):
            frozen.fixture_plan('missing', (8, 110, -3), (-10, 105, -20))

    def test_gate_requires_exact_background_and_all_reserved_neighbors(self):
        plan = frozen.fixture_plan('water_depth_0_background', (8, 110, -3), (-10, 105, -20))
        requested = plan['controls']['supported_positive']['cells']
        original = copy.deepcopy(requested)
        expected = frozen.native_reference(requested) + [(plan['platform'], encode(('minecraft:stone', 0)))]
        state = frozen.contained.expected_native(expected, plan['reserved'])
        observed = {'server': snapshot(state), 'client': snapshot(state)}
        gate = frozen.native_gate(observed, observed, plan, requested)
        self.assertTrue(gate['public_snapshot_unchanged'])
        self.assertFalse(gate['geometry_accepted'])
        self.assertTrue(gate['native_layer_conversion_required'])
        self.assertEqual(original, requested)
        self.assertEqual(original, gate['logical_cells'])
        self.assertEqual(frozen.native_reference(original), gate['native_reference_cells'])
        for position, replacement in (
                (tuple(plan['cell_origin']), (AIR, ('minecraft:water', 0), False)),
                (tuple(plan['cavity'][0]), (AIR, ('minecraft:flowing_water', 7), False))):
            changed = dict(state)
            changed[position] = replacement
            after = {'server': snapshot(state), 'client': snapshot(changed)}
            self.assertFalse(frozen.native_gate(observed, after, plan, requested)['public_snapshot_unchanged'])

    def test_native_reference_keeps_water_depth_and_does_not_mutate_logical_control(self):
        from projection.cell import make_cell
        pos = (8, 110, -3)
        logical = [(pos, encode(make_cell(AIR, ('minecraft:flowing_water', 3))))]
        original = copy.deepcopy(logical)
        self.assertEqual([(pos, encode(('minecraft:flowing_water', 3)))], frozen.native_reference(logical))
        self.assertEqual(original, logical)
        logical = [(pos, encode(make_cell(('minecraft:oak_fence', 0), ('minecraft:water', 0))))]
        self.assertEqual(logical, frozen.native_reference(logical))

    def test_invalid_native_snapshot_cannot_pass(self):
        plan = frozen.fixture_plan('water_depth_0_foreground', (8, 110, -3), (-10, 105, -20))
        state = frozen.contained.expected_native(
            [(plan['platform'], encode(('minecraft:stone', 0)))], plan['reserved'])
        observed = {'server': snapshot(state), 'client': snapshot(state)}
        after = copy.deepcopy(observed)
        after['client']['valid'] = False
        gate = frozen.native_gate(observed, after, plan, [])
        self.assertFalse(gate['public_snapshot_unchanged'])
        self.assertEqual(['client:invalid_or_incomplete_snapshot'], gate['failure_reasons'])

    def test_missing_liquid_before_capture_is_distinct_from_capture_time_drift(self):
        plan = frozen.fixture_plan('flowing_water_depth_1_foreground', (8, 110, -3), (-10, 105, -20))
        requested = plan['controls']['supported_positive']['cells']
        expected = frozen.native_reference(requested) + [(plan['platform'], encode(('minecraft:stone', 0)))]
        present = frozen.contained.expected_native(expected, plan['reserved'])
        missing = dict(present)
        missing[plan['cell_origin']] = (AIR, AIR, False)
        before = {'server': snapshot(missing), 'client': snapshot(missing)}
        gate = frozen.native_gate(before, before, plan, requested)
        self.assertFalse(gate['public_snapshot_unchanged'])
        self.assertTrue(all(row['changes']['unchanged'] for row in gate['sides'].values()))
        self.assertEqual([
            'client:requested_context_missing_before_capture',
            'client:requested_context_missing_after_capture',
            'server:requested_context_missing_before_capture',
            'server:requested_context_missing_after_capture'], gate['failure_reasons'])
        before = {'server': snapshot(present), 'client': snapshot(present)}
        after = {'server': snapshot(present), 'client': snapshot(missing)}
        gate = frozen.native_gate(before, after, plan, requested)
        self.assertEqual(['client:requested_context_missing_after_capture',
                          'client:native_layers_changed_during_capture'], gate['failure_reasons'])

    def frozen_report(self, legacy=False):
        plans = [frozen.fixture_plan(identity, (8, 110, -3), (-10, 105, -20))
                 for identity in ('water_depth_0_background', 'water_flow_corner_foreground')]
        cavity = sorted(set(tuple(pos) for plan in plans for pos in plan['cavity']))
        reserved = sorted(set(tuple(pos) for plan in plans for pos in plan['reserved']))
        for plan in plans:
            plan['cavity'], plan['reserved'] = cavity, reserved
            if legacy:
                for control in plan['controls'].values():
                    control.pop('native_cells')
        report = {'schema': 1 if legacy else 2, 'reservation': copy.deepcopy(plans[0]),
                  'cases': [{'case': plan['case'], 'source': plan} for plan in plans]}
        return json.loads(json.dumps(report))

    def test_observation_binder_reconstructs_frozen_neighbors_and_old_logical_sources(self):
        for legacy in (False, True):
            report = self.frozen_report(legacy)
            original = copy.deepcopy(report)
            expected = recorder.frozen_plans(report)
            for case in report['cases']:
                self.assertEqual(case['source'], json.loads(json.dumps(expected[case['case']])))
            self.assertEqual(original, report)
            report['reservation']['reserved'].pop()
            with self.assertRaisesRegex(ValueError, 'reservation differs'):
                recorder.frozen_plans(report)

    def test_observation_binder_rejects_duplicate_cases_and_origin_changes(self):
        report = self.frozen_report()
        report['cases'].append(report['cases'][0])
        with self.assertRaisesRegex(ValueError, 'unique'):
            recorder.frozen_plans(report)
        report = self.frozen_report()
        report['cases'][1]['source']['cell_origin'][0] += 1
        with self.assertRaisesRegex(ValueError, 'share'):
            recorder.frozen_plans(report)


if __name__ == '__main__':
    unittest.main()
