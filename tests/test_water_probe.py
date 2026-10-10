import runpy
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class ProbeRuntime(object):
    def __init__(self, fail=False, extra_states=0, load_delay=0, mismatch=False, wet_changes=False,
                 fluids=False, air_none=False, paired=False, native_bed_water=True):
        self.blocks, self.liquids, self.callbacks = {}, {}, []
        self.calls, self.clock, self.fail = 0, 0.0, fail
        self.extra_states, self.load_delay, self.mismatch = extra_states, load_delay, mismatch
        self.wet_changes = wet_changes
        self.fluids, self.air_none = fluids, air_none
        self.paired, self.native_bed_water = paired, native_bed_water
        self.pair_palettes = []
        self.entity_reads = []
        self.logs = []
        self.area, self.deleted, self.subchunk_states, self.requested_aux = None, [], {}, []

    def time(self):
        self.clock += .001
        return self.clock

    def GetBlockNew(self, pos, dimension):
        return self.blocks.get(pos, {'name': 'minecraft:air', 'aux': 0})

    def GetLiquidBlock(self, pos, dimension):
        return self.liquids.get(pos)

    def GetBlockEntityData(self, dimension, pos):
        value = self.blocks[pos]
        self.entity_reads.append(value['name'])
        if value['name'] == 'minecraft:fence':
            return {'id': {'__type__': 8, '__value__': 'MockNativeFixtureEntity'},
                    'x': {'__type__': 3, '__value__': pos[0]}}
        return None

    def GetBlockAuxValueFromStates(self, name, states):
        return (states.get('test_aux', states.get('direction', 0) +
                           2 * int(states.get('head_piece_bit', False))) + 16)

    def GetBlockStates(self, pos, dimension):
        value = self.blocks[pos]
        if self.air_none and value['name'] == 'minecraft:air':
            return None
        aux = value['aux']
        if 'states' in value:
            return dict(value['states'])
        return {'test_aux': aux + 1 if self.mismatch and value['name'] == 'minecraft:stairs' else aux}

    def SetBlockStates(self, pos, states, dimension):
        self.blocks[pos]['aux'] = states['test_aux']
        value = self.blocks[pos]
        if value['name'] == 'minecraft:stairs' and value['aux'] != 0:
            self.liquids.pop(pos, None)
        return True

    def GetBlankBlockPalette(self):
        return self

    def DeserializeBlockPalette(self, data):
        self.palette_data = data
        return True

    def SetBlockByBlockPalette(self, palette, dimension, origin, rotation, conflict):
        data = self.palette_data
        self.pair_palettes.append(data)
        sz, sx, sy = data['volume']
        for key, indices in data['common'].items():
            properties = data['states'][key]
            properties = dict((name.decode('utf8') if isinstance(name, bytes) else name, value)
                              for name, value in properties.items())
            for index in indices:
                local = ((index // sz) % sx, index // (sz * sx), index % sz)
                pos = tuple(origin[i] + local[i] for i in range(3))
                self.blocks[pos] = {'name': key[0].decode('utf8'), 'aux': key[1],
                                    'states': properties}
                self.liquids.pop(pos, None)
        for key, indices in data['extra'].items():
            for index in indices:
                local = ((index // sz) % sx, index // (sz * sx), index % sz)
                pos = tuple(origin[i] + local[i] for i in range(3))
                self.liquids[pos] = {'name': key[0].decode('utf8'), 'aux': key[1]}
        return True

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
            if self.fluids:
                value['name'] = {'minecraft:flowing_water': 'minecraft:water',
                                 'minecraft:flowing_lava': 'minecraft:lava'}.get(value['name'], value['name'])
        if self.fail and value['name'] == 'minecraft:stairs':
            raise RuntimeError('native probe failure')
        if self.wet_changes and value['name'] == 'minecraft:stairs' and pos in self.liquids:
            value = {'name': 'minecraft:water', 'aux': 0}
        self.blocks[pos] = value
        if value['name'] == 'minecraft:water':
            self.liquids[pos] = value
        elif (value['name'] != 'minecraft:fence' and
              not (value['name'] == 'minecraft:bed' and self.native_bed_water) and not (
                value['name'] == 'minecraft:stairs' and value['aux'] == 0)):
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
                CreateBlock=lambda level: self,
                CreatePos=lambda player: types.SimpleNamespace(GetFootPos=lambda: (0., 64., 0.))),
            GetPlayerList=lambda: ['player'], GetLevelId=lambda: 'level')
        values = {'minecraft:air': (0,), 'minecraft:fence': (0, 1),
                  'minecraft:stairs': (0, 1, 2, 3), 'minecraft:stone': (0,)}
        if self.extra_states:
            values['minecraft:probe'] = tuple(range(self.extra_states))
        if self.fluids:
            for name in ('water', 'flowing_water', 'lava', 'flowing_lava'):
                values['minecraft:' + name] = (0, 1)
        if self.paired:
            values['minecraft:bed'] = (0, 1, 2, 3)

        def states(value):
            if self.air_none and value[0] == 'minecraft:air':
                return {}
            if value[0] == 'minecraft:bed':
                return {'direction': value[1] % 2, 'head_piece_bit': value[1] >= 2,
                        'occupied_bit': False}
            return {'test_aux': value[1]}

        def partner(value):
            if value[0] != 'minecraft:bed':
                return None
            offset = (0, 0, 1) if value[1] % 2 == 0 else (-1, 0, 0)
            if value[1] >= 2:
                offset = tuple(-coord for coord in offset)
            return offset, (value[0], (value[1] + 2) % 4)
        registry = types.SimpleNamespace(
            BLOCKS=values, DEFAULT_AUX=dict((name, 0) for name in values),
            aux_values=lambda name: values[name],
            states=states, canonical=lambda value: value,
            source_version=lambda: 'Test native version', fingerprint=lambda: 'native-hash')
        return {'mod': types.ModuleType('mod'), 'mod.server': types.ModuleType('mod.server'),
                'mod.server.extraServerApi': api,
                'modern_projection': types.ModuleType('modern_projection'),
                'modern_projection.projection': types.SimpleNamespace(
                    block_registry=registry, block_groups=types.SimpleNamespace(group_partner=partner))}


class WaterProbeTests(unittest.TestCase):
    def tearDown(self):
        if hasattr(sys, '_p0_native_probe'):
            del sys._p0_native_probe
        if hasattr(sys, '_p0_probe_run'):
            del sys._p0_probe_run

    def start(self, runtime):
        with patch.dict(sys.modules, runtime.modules()), patch('time.time', runtime.time), \
                patch('builtins.print', side_effect=runtime.logs.append):
            values = runpy.run_path(str(ROOT / 'tools/dump_waterloggable_blocks.py'))
            runtime.probe = values['_probe']
        return sys._p0_native_probe

    def finish(self, runtime):
        with patch('time.time', runtime.time), patch('builtins.print', side_effect=runtime.logs.append):
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
        self.assertEqual(state['readback_states']['minecraft:stairs']['3']['dry']['states'],
                         {'test_aux': 3})
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
        self.assertEqual({'test_aux': 1}, state['readback_states']['minecraft:stairs']['0']['dry']['states'])
        self.assertEqual(4, state['verified_states'])
        with patch('time.time', runtime.time), self.assertRaisesRegex(ValueError, 'probe failed'):
            runpy.run_path(str(ROOT / 'tools/p0_water_probe_read.py'))

    def test_normal_wet_block_replacement_is_negative_without_invalidating_dry_state_verification(self):
        runtime = ProbeRuntime(wet_changes=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertEqual([], state['state_mismatches'])
        self.assertEqual(state['tested_states'], state['verified_states'])
        self.assertFalse(state['results']['minecraft:stairs'])
        self.assertEqual('minecraft:stairs',
                         state['readback_states']['minecraft:stairs']['0']['dry']['front']['name'])
        self.assertEqual('minecraft:water',
                         state['readback_states']['minecraft:stairs']['0']['wet']['front']['name'])

    def test_successive_probe_runs_use_fresh_subchunk_columns(self):
        runtime = ProbeRuntime()
        first = self.start(runtime)
        self.finish(runtime)
        second = self.start(runtime)
        self.finish(runtime)
        self.assertEqual(1, first['probe_run'])
        self.assertEqual(2, second['probe_run'])
        self.assertEqual(160, second['target'][0] - first['target'][0])
        self.assertEqual(160, second['min_pos'][0] - first['min_pos'][0])
        self.assertNotEqual(first['area_key'], second['area_key'])

    def test_semantic_aux_variants_use_native_default_seed_before_explicit_states(self):
        runtime = ProbeRuntime(extra_states=40)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertEqual({16}, set(runtime.requested_aux))
        record = state['readback_states']['minecraft:probe']['39']
        self.assertEqual(55, record['native_aux'])
        self.assertEqual(16, record['seed_aux'])
        self.assertEqual({'test_aux': 39}, record['dry']['states'])

    def test_native_flowing_liquid_aliases_verify_semantically_and_never_compose(self):
        runtime = ProbeRuntime(fluids=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertEqual(state['tested_states'], state['verified_states'])
        for name in ('water', 'flowing_water', 'lava', 'flowing_lava'):
            self.assertFalse(state['results']['minecraft:' + name])
        self.assertEqual('minecraft:water',
                         state['readback_states']['minecraft:flowing_water']['1']['dry']['front']['name'])

    def test_native_air_without_state_dictionary_is_an_empty_verified_state(self):
        runtime = ProbeRuntime(air_none=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertEqual({}, state['readback_states']['minecraft:air']['0']['dry']['states'])
        self.assertFalse(state['results']['minecraft:air'])

    def test_paired_beds_write_both_precise_halves_and_preserve_only_native_retained_water(self):
        runtime = ProbeRuntime(paired=True)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertTrue(state['results']['minecraft:bed'])
        self.assertEqual(8, len(runtime.pair_palettes))
        self.assertTrue(any('paired SetBlockByBlockPalette begin' in line for line in runtime.logs))
        self.assertTrue(any('paired fixture complete' in line for line in runtime.logs))
        for aux in range(4):
            record = state['readback_states']['minecraft:bed'][str(aux)]
            self.assertEqual(bool(aux >= 2), record['dry']['states']['head_piece_bit'])
            self.assertTrue(record['fixture']['paired'])
            self.assertEqual('minecraft:water', record['native_retained_liquid']['name'])
        self.assertTrue(all(block['name'] == 'minecraft:air' for block in runtime.blocks.values()))

    def test_pair_state_repair_never_adds_water_if_native_placement_did_not_retain_it(self):
        runtime = ProbeRuntime(paired=True, native_bed_water=False)
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIsNone(state['failure'])
        self.assertFalse(state['results']['minecraft:bed'])
        self.assertTrue(all(not data['extra'] for data in runtime.pair_palettes))
        self.assertEqual(state['total_states'], state['verified_states'])

    def test_all_paired_scratch_cells_are_checked_before_any_world_mutation(self):
        runtime = ProbeRuntime()
        runtime.blocks[(201, 113, 40)] = {'name': 'minecraft:stone', 'aux': 0}
        state = self.start(runtime)
        self.finish(runtime)
        self.assertIn('empty disposable cells', state['failure'])
        self.assertEqual(0, runtime.calls)
        self.assertEqual('minecraft:stone', runtime.blocks[(201, 113, 40)]['name'])

    def test_default_entity_nbt_is_read_once_per_verified_native_name_and_exported(self):
        runtime = ProbeRuntime()
        state = self.start(runtime)
        self.finish(runtime)
        self.assertEqual(4, len(runtime.entity_reads))
        self.assertEqual(1, runtime.entity_reads.count('minecraft:fence'))
        self.assertEqual(1, runtime.entity_reads.count('minecraft:stone'))
        self.assertEqual(set(state['results']), set(state['block_entity_names']))
        self.assertEqual({'minecraft:fence'}, set(state['block_entities']))
        self.assertEqual(0, state['block_entities']['minecraft:fence']['aux'])
        self.assertEqual({'__type__': 8, '__value__': 'MockNativeFixtureEntity'},
                         state['block_entities']['minecraft:fence']['nbt']['id'])
        export = runpy.run_path(str(ROOT / 'tools/p0_water_probe_read.py'))
        self.assertIn('block_entities', export['_result'])


if __name__ == '__main__':
    unittest.main()
