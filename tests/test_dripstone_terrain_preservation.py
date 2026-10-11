"""Terrain-backed probes must reject unsafe cells and verify exact rollback."""
import copy
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_dripstone_native_boxes as diagnostic


class NativePalette:
    def __init__(self, runtime, data=None):
        self.runtime, self.data = runtime, copy.deepcopy(data)

    def SerializeBlockPalette(self):
        return copy.deepcopy(self.data)

    def DeserializeBlockPalette(self, data):
        self.data = copy.deepcopy(data)
        if self.runtime.lossy_palette:
            self.data['states'] = {}
        return True


class TerrainRuntime:
    def __init__(self):
        self.blocks, self.calls = {}, []
        self.foot = (1.5, 64., 2.5)
        self.writes, self.fail_write, self.fail_restore = 0, None, None
        self.lossy_palette = False

    def row(self, pos):
        return self.blocks.get(pos, {'front': {'name': 'minecraft:air', 'aux': 0},
                                     'liquid': None, 'states': None, 'entity_nbt': None})

    def put(self, pos, name='minecraft:tuff', aux=0, states=None, **fields):
        self.blocks[pos] = dict(front={'name': name, 'aux': aux}, liquid=None,
                                states={} if states is None else states, entity_nbt=None)
        self.blocks[pos].update(fields)

    def GetBlockPaletteBetweenPos(self, dimension, low, high, void):
        self.calls.append(('palette_read', low))
        row = self.row(low)
        key = (row['front']['name'], row['front']['aux'])
        data = {'volume': (1, 1, 1), 'common': {key: [0]},
                'extra': row.get('extra', {('minecraft:air', 0): [0]}),
                'states': {key: row['states'] or {}}, 'extraStates': {},
                'actor': row.get('actor', {}), 'void': False, 'eliminateAir': False}
        return NativePalette(self, data)

    def GetBlankBlockPalette(self):
        return NativePalette(self)

    def GetBlockNew(self, pos, dimension):
        self.calls.append(('front_read', pos))
        return copy.deepcopy(self.row(pos)['front'])

    def GetLiquidBlock(self, pos, dimension):
        self.calls.append(('liquid_read', pos))
        return copy.deepcopy(self.row(pos)['liquid'])

    def GetBlockStates(self, pos, dimension):
        self.calls.append(('states_read', pos))
        return copy.deepcopy(self.row(pos)['states'])

    def GetBlockEntityData(self, dimension, pos):
        self.calls.append(('nbt_read', pos))
        return copy.deepcopy(self.row(pos)['entity_nbt'])

    def GetFootPos(self):
        return self.foot

    def SetFootPos(self, foot):
        self.foot = tuple(foot)
        return True

    def SetBlockByBlockPalette(self, palette, dimension, pos, rotation, conflict):
        self.calls.append(('restore_write', pos))
        if pos == self.fail_restore:
            raise RuntimeError('injected restore failure')
        key = next(iter(palette.data['common']))
        self.put(pos, key[0], key[1], palette.data['states'][key])
        if key[0] == 'minecraft:air':
            self.blocks[pos]['states'] = None
        return True

    def modules(self):
        runtime = self

        class Adapter:
            dimension = 0

            def __init__(self, player):
                pass

            def read(self, pos):
                front = runtime.row(pos)['front']
                return front['name'], front['aux']

            def write(self, pos, value):
                runtime.calls.append(('fixture_write', pos))
                runtime.writes += 1
                if runtime.writes == runtime.fail_write:
                    raise RuntimeError('injected fixture failure')
                runtime.put(pos, value[0], value[1])
                if value[0] == 'minecraft:air':
                    runtime.blocks[pos]['states'] = None
                return True

        factory = types.SimpleNamespace(
            CreateBlock=lambda level: self, CreateBlockInfo=lambda level: self,
            CreateBlockState=lambda level: self, CreatePos=lambda player: self)
        api = types.SimpleNamespace(GetPlayerList=lambda: ['player'],
                                    GetLevelId=lambda: 'level', GetEngineCompFactory=lambda: factory)
        return {'mod': types.ModuleType('mod'), 'mod.server': types.ModuleType('mod.server'),
                'mod.server.extraServerApi': api,
                'modern_projection': types.ModuleType('modern_projection'),
                'modern_projection.projection': types.ModuleType('modern_projection.projection'),
                'modern_projection.projection.cell': types.SimpleNamespace(AIR=('minecraft:air', 0)),
                'modern_projection.server_system': types.SimpleNamespace(WorldAdapter=Adapter)}


class TerrainPreservationTests(unittest.TestCase):
    cells = [((6, -37, 6), ('minecraft:pointed_dripstone', 4))]
    supports = [((6, -38, 6), ('minecraft:stone', 0))]
    near = [((0, -47, 0), ('minecraft:air', 0))]
    terrain_pos = (6, -38, 6)

    def tearDown(self):
        if hasattr(sys, '_neighbor_world_saved'):
            del sys._neighbor_world_saved

    def execute(self, runtime, code):
        import json
        with patch.dict(sys.modules, runtime.modules()):
            namespace = {}
            exec(code, namespace)
        return json.loads(namespace['_result'])

    def reserve(self, runtime):
        return self.execute(runtime, diagnostic.RESERVE_PRESERVED % (
            self.cells, self.supports, self.near, diagnostic.PRESERVABLE_TERRAIN))

    def test_all_preflight_fields_precede_writes_and_native_terrain_is_restored(self):
        runtime = TerrainRuntime()
        runtime.put(self.terrain_pos, 'minecraft:basalt', 2, {'pillar_axis': 'x'})
        original = copy.deepcopy(runtime.row(self.terrain_pos))
        before_foot = runtime.foot
        result = self.reserve(runtime)
        self.assertTrue(result['all_preflight_reads_before_write'])
        first_write = next(index for index, call in enumerate(runtime.calls) if call[0] == 'fixture_write')
        reads = runtime.calls[:first_write]
        saved = sys._neighbor_world_saved
        positions = {row['pos'] for row in saved['snapshots']}
        for field in ('palette_read', 'front_read', 'liquid_read', 'states_read', 'nbt_read'):
            self.assertEqual(positions, {pos for kind, pos in reads if kind == field})
        self.assertIn((-4, -48, -4), positions)
        self.assertGreater(len(saved['guard']), 0)
        self.execute(runtime, diagnostic.NEAR_PRESERVED_PLAYER)
        cleanup = self.execute(runtime, diagnostic.CLEAR_PRESERVED)
        self.assertTrue(cleanup['restored'], cleanup)
        self.assertEqual(cleanup['verified_cells'], len(positions))
        self.assertEqual(original, runtime.row(self.terrain_pos))
        self.assertEqual(before_foot, runtime.foot)
        self.assertFalse(hasattr(sys, '_neighbor_world_saved'))

    def test_unsupported_layers_actors_and_lossy_snapshots_reject_without_writes(self):
        cases = [dict(name='minecraft:gravel'), dict(name='minecraft:chest'),
                 dict(liquid={'name': 'minecraft:water', 'aux': 0}),
                 dict(entity_nbt={'id': 'unexpected'}), dict(actor={(0, 0, 0): {'id': 'unexpected'}}),
                 dict(extra={('minecraft:water', 0): [0]})]
        for fields in cases:
            runtime = TerrainRuntime()
            runtime.put(self.terrain_pos, **fields)
            with self.subTest(fields=fields), self.assertRaises(AssertionError):
                self.reserve(runtime)
            self.assertEqual(runtime.writes, 0)
            self.assertFalse(hasattr(sys, '_neighbor_world_saved'))
            self.assertTrue(self.execute(runtime, diagnostic.CLEAR_PRESERVED)['restored'])
        runtime = TerrainRuntime()
        runtime.put(self.terrain_pos, 'minecraft:basalt', 2, {'pillar_axis': 'x'})
        runtime.lossy_palette = True
        with self.assertRaises(AssertionError):
            self.reserve(runtime)
        self.assertEqual(runtime.writes, 0)

    def test_partial_fixture_failure_restores_every_saved_cell(self):
        runtime = TerrainRuntime()
        runtime.put(self.terrain_pos)
        runtime.fail_write = 2
        with self.assertRaises(RuntimeError):
            self.reserve(runtime)
        saved_count = len(sys._neighbor_world_saved['snapshots'])
        cleanup = self.execute(runtime, diagnostic.CLEAR_PRESERVED)
        self.assertTrue(cleanup['restored'], cleanup)
        self.assertEqual(saved_count, cleanup['verified_cells'])
        self.assertEqual(runtime.row(self.terrain_pos)['front']['name'], 'minecraft:tuff')

    def test_failed_restore_continues_and_retains_snapshot_for_retry(self):
        runtime = TerrainRuntime()
        runtime.put(self.terrain_pos)
        self.reserve(runtime)
        runtime.fail_restore = self.terrain_pos
        cleanup = self.execute(runtime, diagnostic.CLEAR_PRESERVED)
        self.assertFalse(cleanup['restored'])
        self.assertTrue(cleanup['snapshot_retained_for_retry'])
        self.assertTrue(hasattr(sys, '_neighbor_world_saved'))
        self.assertEqual(runtime.row((-4, -48, -4))['front']['name'], 'minecraft:air')
        runtime.fail_restore = None
        self.assertTrue(self.execute(runtime, diagnostic.CLEAR_PRESERVED)['restored'])

    def test_changed_guard_cell_is_restored_and_verified(self):
        runtime = TerrainRuntime()
        self.reserve(runtime)
        guard = min(sys._neighbor_world_saved['guard'])
        runtime.put(guard, 'minecraft:stone', 0)
        cleanup = self.execute(runtime, diagnostic.CLEAR_PRESERVED)
        self.assertTrue(cleanup['restored'], cleanup)
        self.assertEqual(runtime.row(guard)['front']['name'], 'minecraft:air')

    def test_fixture_replication_ignores_saved_surrounding_terrain_and_rejects_stale_aux(self):
        import json
        values = dict(self.cells + self.supports)
        values[(7, -37, 6)] = ('minecraft:tuff', 0)
        info = types.SimpleNamespace(GetBlock=lambda pos: dict(name=values[pos][0], aux=values[pos][1]))
        bridge = types.SimpleNamespace(level='level', factory=types.SimpleNamespace(CreateBlockInfo=lambda level: info))
        namespace = {'b': bridge, 'json': json}
        code = diagnostic.REPLICATION_PRESERVED % (self.cells + self.supports,)
        exec(code, namespace)
        self.assertTrue(json.loads(namespace['_result'])['matches'])
        values[self.cells[0][0]] = ('minecraft:pointed_dripstone', 12)
        exec(code, namespace)
        self.assertFalse(json.loads(namespace['_result'])['matches'])

    def test_python2_payloads_compile(self):
        pypy = Path('C:/Users/Happy2018new/Desktop/PyPy/pypy2.exe')
        if not pypy.is_file():
            self.skipTest('Local game-compatible Python 2 interpreter is unavailable')
        reserve = diagnostic.RESERVE_PRESERVED % (self.cells, self.supports, self.near,
                                                diagnostic.PRESERVABLE_TERRAIN)
        script = '\n'.join('compile(%r,%r,"exec")' % (code, 'payload_' + str(index))
                           for index, code in enumerate((reserve, diagnostic.NEAR_PRESERVED_PLAYER,
                                                        diagnostic.CLEAR_PRESERVED,
                                                        diagnostic.REPLICATION_PRESERVED % (self.cells,))))
        completed = subprocess.run([str(pypy), '-c', script], capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()
