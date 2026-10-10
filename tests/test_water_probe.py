import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ProbeRuntime(object):
    def __init__(self, fail=False):
        self.blocks, self.liquids, self.callbacks = {}, {}, []
        self.calls, self.clock, self.fail = 0, 0.0, fail

    def time(self):
        self.clock += .001
        return self.clock

    def GetBlockNew(self, pos, dimension):
        return self.blocks.get(pos, {'name': 'minecraft:air', 'aux': 0})

    def GetLiquidBlock(self, pos, dimension):
        return self.liquids.get(pos)

    def SetLiquidBlock(self, pos, value, dimension):
        self.liquids.pop(pos, None)

    def SetBlockNew(self, pos, value, handling, dimension, legacy, neighbors):
        self.calls += 1
        if not legacy or neighbors:
            raise AssertionError('Native probe must use fixed legacy states without neighbor updates')
        value = dict(value)
        if isinstance(value['name'], bytes):
            value['name'] = value['name'].decode('utf8')
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
                CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0., 64., 0.))),
            GetPlayerList=lambda: ['player'], GetLevelId=lambda: 'level')
        values = {'minecraft:air': (0,), 'minecraft:fence': (0, 1),
                  'minecraft:stairs': (0, 1, 2, 3), 'minecraft:stone': (0,)}
        registry = types.SimpleNamespace(
            BLOCKS=values, aux_values=lambda name: values[name],
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
            runpy.run_path(str(ROOT / 'tools/dump_waterloggable_blocks.py'))
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

    def test_native_failure_is_recorded_and_disposable_world_cells_are_cleaned(self):
        runtime = ProbeRuntime(fail=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertTrue(state['done'])
        self.assertFalse(state['running'])
        self.assertEqual('native probe failure', state['failure'])
        self.assertEqual('minecraft:air', runtime.blocks[state['target']]['name'])
        self.assertEqual('minecraft:air', runtime.blocks[state['support']]['name'])


if __name__ == '__main__':
    unittest.main()
