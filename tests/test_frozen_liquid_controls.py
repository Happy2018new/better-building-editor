"""Public-source and layer-drift gates; no native pixels are accepted here."""
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import capture_frozen_liquid_controls as frozen
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
        expected = requested + [(plan['platform'], encode(('minecraft:stone', 0)))]
        state = frozen.contained.expected_native(expected, plan['reserved'])
        observed = {'server': snapshot(state), 'client': snapshot(state)}
        gate = frozen.native_gate(observed, observed, plan, requested)
        self.assertTrue(gate['public_snapshot_unchanged'])
        self.assertFalse(gate['geometry_accepted'])
        for position, replacement in (
                (tuple(plan['cell_origin']), (('minecraft:water', 0), AIR, False)),
                (tuple(plan['cavity'][0]), (AIR, ('minecraft:flowing_water', 7), False))):
            changed = dict(state)
            changed[position] = replacement
            after = {'server': snapshot(state), 'client': snapshot(changed)}
            self.assertFalse(frozen.native_gate(observed, after, plan, requested)['public_snapshot_unchanged'])

    def test_invalid_native_snapshot_cannot_pass(self):
        plan = frozen.fixture_plan('water_depth_0_foreground', (8, 110, -3), (-10, 105, -20))
        state = frozen.contained.expected_native(
            [(plan['platform'], encode(('minecraft:stone', 0)))], plan['reserved'])
        observed = {'server': snapshot(state), 'client': snapshot(state)}
        after = copy.deepcopy(observed)
        after['client']['valid'] = False
        self.assertFalse(frozen.native_gate(observed, after, plan, [])['public_snapshot_unchanged'])


if __name__ == '__main__':
    unittest.main()
