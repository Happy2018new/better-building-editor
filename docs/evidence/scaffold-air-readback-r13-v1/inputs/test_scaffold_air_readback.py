"""Check readonly diagnostic boundaries and preserve unavailable native states."""
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_scaffold_air_readback as probe


class ScaffoldAirReadbackTests(unittest.TestCase):
    def execute(self, players):
        calls = []
        class Position:
            def GetFootPos(self):
                return (.5, -60., .5)
        class Dimension:
            def GetEntityDimensionId(self):
                return 0
        class Native:
            def GetBlockNew(self, pos, dimension):
                calls.append(('block', pos, dimension))
                return {'name': 'minecraft:grass_block' if pos[1] == -61 else 'minecraft:air', 'aux': 0}
            def GetBlockStates(self, pos, dimension):
                calls.append(('states', pos, dimension))
                return {} if pos[1] == -61 else None
            def GetLiquidBlock(self, pos, dimension):
                calls.append(('liquid', pos, dimension))
                return None
        class Factory:
            def CreatePos(self, player):
                self_player = player
                self.assert_player(self_player)
                return Position()
            def assert_player(self, player):
                if player != 'player':
                    raise AssertionError(player)
            def CreateDimension(self, player):
                self.assert_player(player)
                return Dimension()
            def CreateBlockInfo(self, level):
                return Native()
            def CreateBlockState(self, level):
                return Native()
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetPlayerList = lambda: players
        api.GetMinecraftVersion = lambda: probe.RUNTIME
        api.GetLevelId = lambda: 'level'
        api.GetEngineCompFactory = lambda: Factory()
        mod, server = types.ModuleType('mod'), types.ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        with patch.dict(sys.modules, {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api}):
            scope = {}
            exec(compile(probe.SERVER, 'scaffold-air-readback', 'exec'), scope)
        self.assertNotIn('_scaffold_air_readback', scope)
        return scope['_result'], calls

    def test_both_planes_keep_raw_nulls_and_exact_offsets_without_writes(self):
        result, calls = self.execute(['player'])
        self.assertEqual({}, result['ground']['states'])
        self.assertEqual([], result['mutations'])
        self.assertEqual([2, 18], [plane['height_above_foot'] for plane in result['planes']])
        self.assertEqual([(4, -58, 4), (4, -42, 4)], [plane['origin'] for plane in result['planes']])
        for plane in result['planes']:
            self.assertEqual(list(probe.OFFSETS), [cell['offset'] for cell in plane['cells']])
            self.assertTrue(all(cell['states'] is None for cell in plane['cells']))
            self.assertEqual(17, len({cell['pos'] for cell in plane['cells']}))
        self.assertEqual(105, len(calls))
        self.assertEqual({'block', 'states', 'liquid'}, {call[0] for call in calls})

    def test_absent_player_remains_pending_without_reads(self):
        result, calls = self.execute([])
        self.assertIsNone(result['ground'])
        self.assertEqual([], result['planes'])
        self.assertEqual([], calls)

    def test_readonly_payload_compiles_in_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game-compatible Python2 unavailable')
        result = subprocess.run([str(pypy), '-c', 'compile(%r,"scaffold-air","exec")' % probe.SERVER],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
