"""Single-door diagnosis preserves both native half states through failed setters."""
import copy
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_single_door as probe


class NativeSingleDoorTests(unittest.TestCase):
    def native_setup(self, fail_state=False):
        rows, support, reserved = probe.single_pair((4, -48, 4))
        values, properties, calls = {}, {}, []
        foot = (.5, -60., .5)
        class Info:
            def GetBlockNew(self, pos, dimension):
                return values.get(pos, {'name': 'minecraft:air', 'aux': 0})
            def GetLiquidBlock(self, pos, dimension):
                return None
            def SetBlockNew(self, pos, value, handling, dimension, legacy, updates):
                calls.append((pos, copy.deepcopy(value), updates))
                value = dict(value)
                if isinstance(value['name'], bytes):
                    value['name'] = value['name'].decode('utf8')
                changed = self.GetBlockNew(pos, dimension) != value
                values[pos] = value
                if value['name'] == 'minecraft:wooden_door':
                    properties[pos] = copy.deepcopy(rows[int(pos[1] == -47)]['states'])
                    if pos[1] == -48:
                        values[(4, -47, 4)] = {'name': 'minecraft:wooden_door', 'aux': 8}
                        properties[(4, -47, 4)] = copy.deepcopy(rows[1]['states'])
                else:
                    properties[pos] = {}
                return changed
        class State:
            def GetBlockStates(self, pos, dimension):
                return properties.get(pos)
            def GetBlockAuxValueFromStates(self, name, data):
                return 8 if data['upper_block_bit'] else 0
            def SetBlockStates(self, pos, data, dimension):
                if fail_state:
                    raise RuntimeError('native state failure')
                properties[pos] = copy.deepcopy(data)
                return True
        info, state = Info(), State()
        factory = SimpleNamespace(CreateBlockInfo=lambda level: info, CreateBlockState=lambda level: state,
                                  CreateDimension=lambda player: SimpleNamespace(GetEntityDimensionId=lambda: 0),
                                  CreatePos=lambda player: SimpleNamespace(GetFootPos=lambda: foot))
        api = ModuleType('mod.server.extraServerApi')
        api.GetEngineCompFactory = lambda: factory
        api.GetLevelId = lambda: 'test-level'
        api.GetPlayerList = lambda: ['test-player']
        api.GetMinecraftVersion = lambda: 'test-runtime'
        server = ModuleType('modern_projection.server_system')
        server.WorldAdapter = SimpleNamespace(_native_tree=lambda value: value)
        modules = {'mod': ModuleType('mod'), 'mod.server': ModuleType('mod.server'),
                   'mod.server.extraServerApi': api, 'modern_projection': ModuleType('modern_projection'),
                   'modern_projection.server_system': server}
        namespace = {}
        with mock.patch.dict(sys.modules, modules):
            try:
                exec(probe.SETUP % (probe.MARKER, rows, support, reserved), namespace)
                report = probe.json.loads(namespace['_result'])
                exec(probe.CLEAR % probe.MARKER, namespace)
                cleanup = probe.json.loads(namespace['_result'])
            finally:
                if hasattr(sys, probe.MARKER):
                    delattr(sys, probe.MARKER)
        return rows, reserved, report, cleanup, calls

    def test_native_no_change_return_is_recorded_with_both_halves_and_exact_states(self):
        rows, reserved, report, cleanup, calls = self.native_setup()
        self.assertIsNone(report['error'])
        self.assertEqual([True, False, True, True], [step['returned'] for step in report['steps']])
        self.assertTrue(all(len(step['both_halves']) == 2 for step in report['steps']))
        self.assertTrue(probe.shapes.replicated(report['after'], rows))
        self.assertTrue(cleanup['restored'])
        self.assertTrue(cleanup['player_unchanged'])
        self.assertEqual(17, len(reserved))
        self.assertTrue(all(updates is False for pos, value, updates in calls))

    def test_native_setter_exception_preserves_actual_halves_and_complete_cleanup(self):
        rows, reserved, report, cleanup, calls = self.native_setup(fail_state=True)
        self.assertIn('native state failure', report['error'])
        self.assertEqual(2, len(report['steps']))
        self.assertEqual(2, len(report['after']['rows']))
        self.assertTrue(cleanup['restored'])
        cleared = {pos for pos, value, updates in calls if value['name'] == 'minecraft:air'}
        self.assertEqual(set(reserved), cleared)


if __name__ == '__main__':
    unittest.main()
