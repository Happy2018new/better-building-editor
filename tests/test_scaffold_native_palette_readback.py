"""False setter returns need complete real-layer readbacks, not liquid guesses."""
import copy
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_scaffold_single_air_runtime as single
import probe_scaffold_palette_air_readback as readonly
import scaffold_native_palette_readback as palette


class NativePaletteReadbackTests(unittest.TestCase):
    def observation(self):
        return {'schema': 1, 'kind': 'scaffold_palette_air_readback', 'runtime': '1.21.120.0', 'mutations': [],
                'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'}, 'cells': [
                    {'label': 'loaded_ground', 'readback': {'front': {'name': 'minecraft:grass_block', 'aux': 0}, 'states': {}}},
                    {'label': 'natural_air', 'readback': {'front': {'name': 'minecraft:air', 'aux': 0}, 'states': None, 'liquid': None},
                     'volume': [1, 1, 1], 'common': [[['minecraft:air', 0], [0]]], 'extra': [],
                     'states_repr': '{}', 'extraStates_repr': '{}', 'actor_repr': '{}'}]}

    def test_encoding_requires_independent_native_ground_and_air_controls(self):
        expected = palette.encoding_from_observation(self.observation())
        self.assertEqual({'common': [[['minecraft:air', 0], [0]]], 'extra': []}, expected)
        for change in ('ground', 'fluid', 'actor', 'extra', 'volume'):
            value = self.observation()
            air = value['cells'][1]
            if change == 'ground':
                value['cells'][0]['readback']['states'] = None
            elif change == 'fluid':
                air['readback']['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            elif change == 'actor':
                air['actor_repr'] = "{'Chest': {}}"
            elif change == 'extra':
                air['extra'] = [[['minecraft:stone', 0], [0]]]
            else:
                air['volume'] = [1, 1, 2]
            with self.subTest(change=change), self.assertRaises(ValueError):
                palette.encoding_from_observation(value)

    def native(self, background_stone=False, missing_palette=False, raw_states=None):
        front = {'name': 'minecraft:air', 'aux': 0}
        extra = {'value': background_stone}
        calls = []
        class Native:
            def GetBlockNew(self, pos, dimension):
                return {'name': 'minecraft:grass_block', 'aux': 0} if pos == (0, -61, 0) else dict(front)
            def GetBlockStates(self, pos, dimension):
                return raw_states if front['name'] == 'minecraft:air' and pos != (0, -61, 0) else {}
            def GetLiquidBlock(self, pos, dimension):
                return None
            def GetBlockPaletteBetweenPos(self, dimension, low, high, eliminate):
                if missing_palette:
                    return None
                name = 'minecraft:grass_block' if low == (0, -61, 0) else front['name']
                data = {'volume': (1, 1, 1), 'common': {(name, 0): [0]},
                        'extra': {('minecraft:stone', 0): [0]} if extra['value'] else {},
                        'states': {}, 'extraStates': {}, 'actor': {}, 'void': False, 'eliminateAir': False}
                return types.SimpleNamespace(SerializeBlockPalette=lambda: data)
            def GetBlankBlockPalette(self):
                return types.SimpleNamespace(DeserializeBlockPalette=lambda value: True)
            def SetBlockNew(self, pos, value, *args):
                calls.append('stone')
                front.update(value)
                return True
            def SetBlockByBlockPalette(self, *args):
                calls.append('air')
                changed = front['name'] != 'minecraft:air'
                front.update(name='minecraft:air', aux=0)
                extra['value'] = False
                return changed
        native = Native()
        factory = types.SimpleNamespace(CreateBlockInfo=lambda value: native, CreateBlock=lambda value: native,
            CreateBlockState=lambda value: native, CreateDimension=lambda value: types.SimpleNamespace(GetEntityDimensionId=lambda: 0),
            CreatePos=lambda value: types.SimpleNamespace(GetFootPos=lambda: (.5, -60., .5)))
        api = types.ModuleType('mod.server.extraServerApi')
        api.GetMinecraftVersion = lambda: '1.21.120.0'
        api.GetPlayerList = lambda: ['player']
        api.GetLevelId = lambda: 'level'
        api.GetEngineCompFactory = lambda: factory
        mod, server = types.ModuleType('mod'), types.ModuleType('mod.server')
        mod.server, server.extraServerApi = server, api
        return {'mod': mod, 'mod.server': server, 'mod.server.extraServerApi': api}, calls

    def execute(self, **flags):
        modules, calls = self.native(**flags)
        expected = palette.encoding_from_observation(self.observation())
        code = single.payload('player', (.5, -60., .5), 0, (4, -58, 4), expected)
        with patch.dict(sys.modules, modules):
            scope = {}
            exec(compile(code, 'air-runtime', 'exec'), scope)
        return scope['_result'], calls

    def test_false_repeated_setter_keeps_failure_status_but_physical_layers_prove_restore(self):
        result, calls = self.execute()
        self.assertTrue(result['completed'])
        self.assertTrue(result['restored'])
        self.assertIsNone(result['initial']['states'])
        self.assertIs(result['cleanup']['returned'], False)
        self.assertIs(result['cleanup']['setter_success'], False)
        self.assertIs(result['cleanup']['physical_readback_verified'], True)
        self.assertEqual(['stone', 'air', 'air'], calls)

    def test_dry_liquid_value_does_not_hide_nonfluid_background_or_missing_palette(self):
        for flags in ({'background_stone': True}, {'missing_palette': True}):
            with self.subTest(flags=flags), self.assertRaises(AssertionError):
                self.execute(**flags)

    def test_all_native_payloads_compile_for_game_python2(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Game Python2 unavailable')
        expected = palette.encoding_from_observation(self.observation())
        for code in (single.payload('player', (.5, -60., .5), 0, (4, -58, 4), expected), readonly.SERVER):
            result = subprocess.run([str(pypy), '-c', 'compile(%r,"air-palette","exec")' % code],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
