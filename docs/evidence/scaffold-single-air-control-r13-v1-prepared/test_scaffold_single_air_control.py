"""Failures after native writes still restore the single scratch coordinate."""
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_scaffold_single_air_control as probe


class SingleAirControlTests(unittest.TestCase):
    def execute(self, fail_stone=False, occupied=False, moved=False):
        calls = []
        value = {'name': 'minecraft:stone' if occupied else 'minecraft:air', 'aux': 0}
        class Position:
            def GetFootPos(self):
                return (.5, -59. if moved else -60., .5)
        class Dimension:
            def GetEntityDimensionId(self):
                return 0
        class Native:
            def GetBlockNew(self, pos, dimension):
                if pos == (0, -61, 0):
                    return {'name': 'minecraft:grass_block', 'aux': 0}
                return dict(value)
            def GetBlockStates(self, pos, dimension):
                return None if value['name'] == 'minecraft:air' and pos != (0, -61, 0) else {}
            def GetLiquidBlock(self, pos, dimension):
                return None
            def SetBlockNew(self, pos, block, old, dimension, legacy, updates):
                calls.append(('stone', pos, dict(block), old, dimension, legacy, updates))
                value.update(block)
                return not fail_stone
            def GetBlankBlockPalette(self):
                return self
            def DeserializeBlockPalette(self, palette):
                calls.append(('deserialize', palette))
                return True
            def SetBlockByBlockPalette(self, palette, dimension, pos, rotation, conflict):
                calls.append(('air', pos, dimension, rotation, conflict))
                value.update({'name': 'minecraft:air', 'aux': 0})
                return True
        class Factory:
            def CreatePos(self, player):
                return Position()
            def CreateDimension(self, player):
                return Dimension()
            def CreateBlockInfo(self, level):
                return Native()
            def CreateBlockState(self, level):
                return Native()
            def CreateBlock(self, level):
                return Native()
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetPlayerList = lambda: ['player']
        api.GetMinecraftVersion = lambda: probe.RUNTIME
        api.GetLevelId = lambda: 'level'
        api.GetEngineCompFactory = lambda: Factory()
        mod, server = types.ModuleType('mod'), types.ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        with patch.dict(sys.modules, {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api}):
            scope = {}
            source = probe.payload('player', (.5, -60., .5), 0, (4, -58, 4))
            exec(compile(source, 'single-air', 'exec'), scope)
        return scope['_result'], calls, value

    def test_native_nulls_are_retained_after_successful_stone_and_air_control(self):
        result, calls, value = self.execute()
        self.assertTrue(result['completed'])
        self.assertTrue(result['restored'])
        self.assertIsNone(result['initial']['states'])
        self.assertEqual({}, result['stone']['readback']['states'])
        self.assertIsNone(result['explicit_air']['readback']['states'])
        self.assertIsNone(result['cleanup']['readback']['states'])
        self.assertTrue(result['cleanup']['raw_states_equal_initial'])
        self.assertEqual(['deserialize', 'stone', 'air', 'air'], [c[0] for c in calls])
        self.assertEqual({'name': 'minecraft:air', 'aux': 0}, value)
        self.assertEqual({'editor': 'pending', 'full': 'pending', 'missing': 'pending'}, result['acceptance'])

    def test_failed_positive_control_still_restores_written_cell(self):
        with patch('traceback.print_exc'):
            result, calls, value = self.execute(fail_stone=True)
        self.assertFalse(result['completed'])
        self.assertTrue(result['restored'])
        self.assertIn('Native stone positive control failed', result['error'])
        self.assertEqual(['deserialize', 'stone', 'air'], [c[0] for c in calls])
        self.assertEqual({'name': 'minecraft:air', 'aux': 0}, value)

    def test_occupied_cell_and_moved_anchor_are_rejected_before_mutation(self):
        for flags in ({'occupied': True}, {'moved': True}):
            with self.subTest(flags=flags), self.assertRaises(AssertionError):
                self.execute(**flags)

    def test_payload_compiles_in_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game-compatible Python2 unavailable')
        source = probe.payload('player', (.5, -60., .5), 0, (4, -58, 4))
        result = subprocess.run([str(pypy), '-c', 'compile(%r,"single-air","exec")' % source],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
