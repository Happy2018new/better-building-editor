import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ProbeRuntime(object):
    def __init__(self, fail=False, extra_states=0, load_delay=0, mismatch=False):
        self.blocks, self.liquids, self.callbacks = {}, {}, []
        self.calls, self.clock, self.fail = 0, 0.0, fail
        self.extra_states, self.load_delay, self.mismatch = extra_states, load_delay, mismatch
        self.area, self.deleted, self.subchunk_states, self.requested_aux = None, [], {}, []

    def time(self):
        self.clock += .001
        return self.clock

    def GetBlockNew(self, pos, dimension):
        return self.blocks.get(pos, {'name': 'minecraft:air', 'aux': 0})

    def GetLiquidBlock(self, pos, dimension):
        return self.liquids.get(pos)

    def GetBlockAuxValueFromStates(self, name, states):
        return states['test_aux'] + 16

    def GetBlockStates(self, pos, dimension):
        value = self.blocks[pos]
        aux = value['aux']
        return {'test_aux': aux + 1 if self.mismatch and value['name'] == 'minecraft:stairs' else aux}

    def SetAddArea(self, key, dimension, minimum, maximum):
        self.area = (key, dimension, minimum, maximum)
        return True

    def CheckChunkState(self, dimension, pos):
        if self.load_delay:
            self.load_delay -= 1
            return False
        return True

    def DeleteArea(self, key):
        self.deleted.append(key)
        return True

    def SetLiquidBlock(self, pos, value, dimension):
        self.liquids.pop(pos, None)

    def SetBlockNew(self, pos, value, handling, dimension, legacy, neighbors):
        self.calls += 1
        if not legacy or neighbors:
            raise AssertionError('Native probe must use fixed legacy states without neighbor updates')
        value = dict(value)
        if isinstance(value['name'], bytes):
            value['name'] = value['name'].decode('utf8')
            self.requested_aux.append(value['aux'])
            value['aux'] -= 16
            subchunk = tuple(coord // 16 for coord in pos)
            self.subchunk_states.setdefault(subchunk, set()).add((value['name'], value['aux']))
        if self.fail and value['name'] == 'minecraft:stairs':
            raise RuntimeError('native probe failure')
        self.blocks[pos] = value
        if value['name'] == 'minecraft:water':
            self.liquids[pos] = value
        elif value['name'] != 'minecraft:fence' and not (
                value['name'] == 'minecraft:stairs' and value['aux'] == 0):
            self.liquids.pop(pos, None)
        return True

    def AddTimer(self, delay, callback):
        self.callbacks.append(callback)

    def modules(self):
        api = types.SimpleNamespace(
            GetEngineCompFactory=lambda: types.SimpleNamespace(
                CreateDimension=lambda player: types.SimpleNamespace(GetEntityDimensionId=lambda: 0),
                CreateBlockInfo=lambda player: self,
                CreateGame=lambda level: self,
                CreateBlockState=lambda level: self,
                CreateChunkSource=lambda level: self,
                CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0., 64., 0.))),
            GetPlayerList=lambda: ['player'], GetLevelId=lambda: 'level')
        values = {'minecraft:air': (0,), 'minecraft:fence': (0, 1),
                  'minecraft:stairs': (0, 1, 2, 3), 'minecraft:stone': (0,)}
        if self.extra_states:
            values['minecraft:probe'] = tuple(range(self.extra_states))
        registry = types.SimpleNamespace(
            BLOCKS=values, aux_values=lambda name: values[name],
            states=lambda value: {'test_aux': value[1]},
            source_version=lambda: 'Test native version', fingerprint=lambda: 'native-hash')
        return {'mod': types.ModuleType('mod'), 'mod.server': types.ModuleType('mod.server'),
                'mod.server.extraServerApi': api,
                'modern_projection': types.ModuleType('modern_projection'),
                'modern_projection.projection': types.SimpleNamespace(block_registry=registry)}


class WaterProbeTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(sys, '_p0_native_probe'):
            del sys._p0_native_probe

    def start(self, runtime):
        with patch.dict(sys.modules, runtime.modules()), patch('time.time', runtime.time):
            values = runpy.run_path(str(ROOT / 'tools/dump_waterloggable_blocks.py'))
            runtime.probe = values['_probe']
        return sys._p0_native_probe

    def finish(self, runtime):
        with patch('time.time', runtime.time):
            while runtime.callbacks:
                runtime.callbacks.pop(0)()

    def test_probe_returns_immediately_and_yields_between_bounded_tick_batches(self):
        runtime = ProbeRuntime()
        state = self.start(runtime)
        self.assertTrue(state['running'])
        self.assertEqual(0, state['tested_states'])
        self.assertEqual(1, len(runtime.callbacks))
        with patch('time.time', runtime.time):
            runtime.callbacks.pop(0)()
        self.assertGreater(state['tested_states'], 0)
        self.assertLess(state['tested_states'], state['total_states'])
        self.finish(runtime)
        self.assertTrue(state['done'])
        self.assertFalse(state['running'])
        self.assertIsNone(state['failure'])
        self.assertEqual({'minecraft:air': False, 'minecraft:fence': True,
                          'minecraft:stairs': [0], 'minecraft:stone': False}, state['results'])
        self.assertEqual(1.0, state['progress'])
        self.assertEqual('minecraft:air', runtime.blocks[state['target']]['name'])
        self.assertEqual('minecraft:air', runtime.blocks[state['support']]['name'])
        self.assertEqual(state['tested_states'], state['verified_states'])
        self.assertEqual(state['readback_states']['minecraft:stairs']['3'], {'test_aux': 3})
        self.assertEqual([state['area_key']], runtime.deleted)
        self.assertTrue(all(aux >= 16 for aux in runtime.requested_aux))

    def test_native_failure_is_recorded_and_disposable_world_cells_are_cleaned(self):
        runtime = ProbeRuntime(fail=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertTrue(state['done'])
        self.assertFalse(state['running'])
        self.assertEqual('native probe failure', state['failure'])
        self.assertEqual('minecraft:air', runtime.blocks[state['target']]['name'])
        self.assertEqual('minecraft:air', runtime.blocks[state['support']]['name'])
        self.assertEqual([state['area_key']], runtime.deleted)

    def test_large_probe_uses_at_most_32_states_per_isolated_subchunk(self):
        runtime = ProbeRuntime(extra_states=80)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertEqual(3, len(runtime.subchunk_states))
        self.assertLessEqual(max(map(len, runtime.subchunk_states.values())), 32)
        self.assertEqual(32, state['states_per_subchunk'])
        for x, y, z in runtime.subchunk_states:
            self.assertGreaterEqual(y, 7)
            self.assertLessEqual(y, 19)
        self.assertTrue(all(block['name'] == 'minecraft:air' for block in runtime.blocks.values()))

    def test_unloaded_cells_yield_before_any_world_mutation(self):
        runtime = ProbeRuntime(load_delay=1)
        state = self.start(runtime)
        with patch('time.time', runtime.time):
            runtime.callbacks.pop(0)()
        self.assertEqual(0, runtime.calls)
        self.assertEqual(0, state['tested_states'])
        self.finish(runtime)
        self.assertIsNone(state['failure'])

    def test_load_timeout_releases_area_without_touching_unloaded_cells(self):
        runtime = ProbeRuntime(load_delay=100)
        state = self.start(runtime)
        runtime.probe.select_cell.__globals__['LOAD_TIMEOUT_SECONDS'] = .001
        self.finish(runtime)
        self.assertIn('did not finish loading', state['failure'])
        self.assertEqual(0, runtime.calls)
        self.assertEqual([state['area_key']], runtime.deleted)

    def test_readback_mismatch_records_native_evidence_and_refuses_export(self):
        runtime = ProbeRuntime(mismatch=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIn('readback mismatch: 4 states', state['failure'])
        self.assertEqual(4, len(state['state_mismatches']))
        self.assertEqual({'test_aux': 1}, state['readback_states']['minecraft:stairs']['0'])
        self.assertEqual(4, state['verified_states'])
        with patch('time.time', runtime.time), self.assertRaisesRegex(ValueError, 'probe failed'):
            runpy.run_path(str(ROOT / 'tools/p0_water_probe_read.py'))


if __name__ == '__main__':
    unittest.main()
