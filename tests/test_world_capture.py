"""Native client palette capture preserves both layers and block actors."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))

from projection.cell import AIR, actor_data, background, foreground, make_cell
from projection.block_registry import states
from projection.model import Document
from projection.world_capture import merge_entity_document, merge_palette, native_actor_cells, restore_omitted_palette_cells, validate_loaded_chunk
from projection.visible_actor import compose_actor, entity_nbt, render_actor


class WorldCaptureTests(unittest.TestCase):
    def wet_actor_source(self):
        sign = ('minecraft:standing_sign', 0)
        pot = ('minecraft:decorated_pot', 0)
        chest = ('minecraft:chest', 2)
        return {
            'volume': (1, 3, 1),
            'common': {sign: [0], pot: [1], chest: [2]},
            'states': {value: states(value) for value in (sign, pot, chest)},
            'extra': {('minecraft:water', 0): [0, 1]},
            'actor': {b'minecraft:water': {
                0: {b'signRealText': b'front', b'signBackText': b'back'},
                1: {b'sherds': [b'minecraft:angler_pottery_sherd'], b'item': {b'Count': 1}},
            }, 'minecraft:chest': {2: {'facingDirection': 2}}},
        }

    def test_native_wet_actor_bucket_is_resolved_per_position_without_mutating_source(self):
        source = self.wet_actor_source()
        original = copy.deepcopy(source)
        document = Document((3, 1, 1))
        merge_palette(document, source, (0, 0, 0), document.size, (100, 64, 200))
        for index in (0, 1):
            self.assertEqual(source['actor'][b'minecraft:water'][index],
                             actor_data(document.get((index, 0, 0))))
            self.assertEqual(('minecraft:water', 0), background(document.get((index, 0, 0))))
        self.assertEqual({'facingDirection': 2}, actor_data(document.get((2, 0, 0))))
        self.assertEqual({'minecraft:standing_sign', 'minecraft:decorated_pot', 'minecraft:chest'},
                         set(document.palette_data()['actor']))
        self.assertEqual(original, source)
        self.assertEqual([((10, 20, 30), foreground(document.get((0, 0, 0)))),
                          ((11, 20, 30), foreground(document.get((1, 0, 0)))),
                          ((12, 20, 30), foreground(document.get((2, 0, 0))))],
                         list(native_actor_cells(source, (10, 20, 30), document.size)))

    def test_actor_bucket_mismatch_requires_matching_water_and_verified_foreground(self):
        for case in ('missing_water', 'wrong_background', 'wrong_actor', 'ordinary_front', 'no_front'):
            source = self.wet_actor_source()
            if case == 'missing_water':
                source['extra'] = {}
            elif case == 'wrong_background':
                source['extra'] = {('minecraft:flowing_water', 0): [0, 1]}
            elif case == 'wrong_actor':
                source['actor']['minecraft:lava'] = source['actor'].pop(b'minecraft:water')
            else:
                value = ('minecraft:oak_fence', 0) if case == 'ordinary_front' else AIR
                source['common'] = {value: [0, 1, 2]}
                source['states'] = {value: states(value)}
            with self.subTest(case=case):
                document = Document((3, 1, 1))
                with self.assertRaises(ValueError):
                    merge_palette(document, source, (0, 0, 0), document.size, (0, 0, 0))
                self.assertEqual({}, document.blocks)
                with self.assertRaises(ValueError):
                    list(native_actor_cells(source, (0, 0, 0), document.size))

    def test_native_actor_and_layer_duplicate_or_invalid_indices_are_rejected(self):
        for case in ('duplicate_actor', 'duplicate_front', 'duplicate_back', 'air_duplicate',
                     'negative_actor', 'outside_actor', 'bool_actor'):
            source = self.wet_actor_source()
            if case == 'duplicate_actor':
                source['actor']['minecraft:standing_sign'] = {0: {}}
            elif case in ('duplicate_front', 'air_duplicate'):
                source['common'][AIR if case == 'air_duplicate' else ('minecraft:stone', 0)] = [0]
            elif case == 'duplicate_back':
                source['extra'][AIR] = [0]
            else:
                index = {'negative_actor': -1, 'outside_actor': 3, 'bool_actor': False}[case]
                source['actor']['minecraft:standing_sign'] = {index: {}}
            with self.subTest(case=case), self.assertRaises(ValueError):
                merge_palette(Document((3, 1, 1)), source, (0, 0, 0), (3, 1, 1), (0, 0, 0))

    def test_copper_chest_full_nbt_hydrates_missing_native_render_fields(self):
        chest = ('minecraft:copper_chest', 2)
        document = Document((2, 1, 1), {(x, 0, 0): make_cell(chest, AIR, {})
                                       for x in range(2)})
        entities = Document(document.size)
        originals = []
        for x in range(2):
            nbt = {'id': {'__type__': 8, '__value__': 'Chest'},
                   'pairx': {'__type__': 3, '__value__': 1 - x},
                   'pairz': {'__type__': 3, '__value__': 0},
                   'Items': {'__type__': 9, '__value__': []}}
            originals.append(nbt)
            entities.blocks[(x, 0, 0)] = make_cell(chest, AIR, compose_actor(None, nbt))
        merge_entity_document(document, entities)
        for x in range(2):
            actor = actor_data(document.get((x, 0, 0)))
            rendered = render_actor(actor)
            self.assertTrue(rendered['chestIsLargeChest'])
            self.assertEqual(x == 0, rendered['chestMainSubChest'])
            self.assertEqual(2, rendered['facingDirection'])
            self.assertEqual(originals[x], entity_nbt(actor))

    def test_entity_merge_restores_omitted_wet_bed_background_and_full_payload(self):
        foot, head = ('minecraft:bed', 3), ('minecraft:bed', 11)
        water = ('minecraft:water', 0)
        document = Document((2, 1, 1), {(0, 0, 0): foot,
                                      (1, 0, 0): make_cell(head, water, {'color': 7})})
        entities = Document(document.size)
        for x, material in enumerate((foot, head)):
            nbt = {'id': {'__type__': 8, '__value__': 'Bed'},
                   'color': {'__type__': 1, '__value__': 7},
                   'custom': {'__type__': 8, '__value__': 'retained'}}
            entities.blocks[(x, 0, 0)] = make_cell(material, water, compose_actor(None, nbt))
        merge_entity_document(document, entities)
        for pos in entities.blocks:
            self.assertEqual(water, background(document.get(pos)))
            self.assertEqual(entity_nbt(actor_data(entities.get(pos))),
                             entity_nbt(actor_data(document.get(pos))))
        self.assertIsNone(render_actor(actor_data(document.get((0, 0, 0)))))
        self.assertEqual({'color': 7}, render_actor(actor_data(document.get((1, 0, 0)))))

    def test_entity_discovery_uses_bounded_missing_cells_and_existing_entity_names(self):
        head = ('minecraft:bed', 11)
        chest = ('minecraft:chest', 2)
        source = {'volume': (1, 4, 1), 'common': {head: [1], chest: [2], AIR: [3]},
                  'actor': {'minecraft:bed': {1: {'color': 7}}}}
        calls = []
        def read(pos):
            calls.append(pos)
            return ('minecraft:bed', 3)
        self.assertEqual([((16, 0, 32), ('minecraft:bed', 3)),
                          ((17, 0, 32), head), ((18, 0, 32), chest)],
                         list(native_actor_cells(source, (16, 0, 32), (4, 1, 1), read)))
        self.assertEqual([(16, 0, 32)], calls)
        self.assertEqual([((17, 0, 32), head), ((18, 0, 32), chest)],
                         list(native_actor_cells(source, (16, 0, 32), (4, 1, 1), lambda pos: AIR)))
        with self.assertRaises(ValueError):
            list(native_actor_cells(source, (16, 0, 32), (4, 1, 1), lambda pos: None))

    def test_native_omitted_door_half_is_read_from_world_without_synthesizing_it(self):
        door = ('minecraft:wooden_door', 1)
        upper = ('minecraft:wooden_door', 9)
        source = {'volume': (1, 2, 2), 'common': {door: [0], AIR: [1, 3]},
                  'states': {door: states(door), AIR: {}}}
        document = Document((2, 2, 1))
        origin = (100, 64, 200)
        merge_palette(document, source, (0, 0, 0), document.size, origin)
        reads = []
        def read(pos):
            reads.append(pos)
            return upper
        restore_omitted_palette_cells(document, source, (0, 0, 0),
                                      document.size, origin, read)
        self.assertEqual([(100, 65, 200)], reads)
        self.assertEqual(upper, foreground(document.get((0, 1, 0))))
        self.assertEqual(AIR, document.get((1, 1, 0)))

    def test_omitted_part_read_preserves_background_and_actual_absence(self):
        source = {'volume': (1, 1, 1), 'common': {},
                  'extra': {('minecraft:water', 0): [0]}}
        document = Document((1, 1, 1))
        merge_palette(document, source, (0, 0, 0), document.size, (0, 0, 0))
        restore_omitted_palette_cells(document, source, (0, 0, 0), document.size,
                                      (0, 0, 0), lambda pos: AIR)
        self.assertEqual(AIR, foreground(document.get((0, 0, 0))))
        self.assertEqual(('minecraft:water', 0), background(document.get((0, 0, 0))))
        with self.assertRaises(ValueError):
            restore_omitted_palette_cells(document, source, (0, 0, 0), document.size,
                                          (0, 0, 0), lambda pos: None)

    def test_palette_indices_layers_states_and_typed_actor_coordinates(self):
        front_stairs = ('minecraft:oak_stairs', 0)
        front_chest = ('minecraft:chest', 0)
        water = ('minecraft:water', 0)
        chest_actor = {
            b'id': {b'__type__': 8, b'__value__': b'Chest'},
            b'x': {b'__type__': 3, b'__value__': 101},
            b'y': {b'__type__': 3, b'__value__': 64},
            b'z': {b'__type__': 3, b'__value__': 200},
            b'pairx': {b'__type__': 3, b'__value__': 102},
            b'Items': [{b'Slot': 0, b'Name': b'minecraft:apple'}],
        }
        document = Document((2, 1, 2))
        source = {
            'volume': (2, 2, 1),
            'common': {front_stairs: [0], front_chest: [2]},
            'states': {
                front_stairs: dict((key.encode('utf8'), value)
                                   for key, value in states(front_stairs).items()),
                front_chest: dict((key.encode('utf8'), value)
                                  for key, value in states(front_chest).items()),
            },
            'extra': {water: [0]},
            'extraStates': {water: states(water)},
            'actor': {'minecraft:chest': {2: chest_actor}},
        }

        merge_palette(document, source, (0, 0, 0), (2, 1, 2), (100, 64, 200))

        stair = document.get((0, 0, 0))
        self.assertEqual(front_stairs, foreground(stair))
        self.assertEqual(water, background(stair))
        chest = document.get((1, 0, 0))
        self.assertEqual(front_chest, foreground(chest))
        self.assertEqual(AIR, background(chest))
        actor = actor_data(chest)
        self.assertEqual(b'Chest', actor[b'id'][b'__value__'])
        self.assertEqual(1, actor[b'x'][b'__value__'])
        self.assertEqual(0, actor[b'y'][b'__value__'])
        self.assertEqual(0, actor[b'z'][b'__value__'])
        self.assertEqual(2, actor[b'pairx'][b'__value__'])
        self.assertEqual(b'minecraft:apple', actor[b'Items'][0][b'Name'])

    def test_palette_shape_and_state_mismatch_fail_without_partial_guessing(self):
        stairs = ('minecraft:oak_stairs', 0)
        document = Document((1, 1, 1))
        with self.assertRaises(ValueError):
            merge_palette(document, {'volume': (2, 1, 1)}, (0, 0, 0),
                          (1, 1, 1), (0, 0, 0))

        source = {
            'volume': (1, 1, 1),
            'common': {stairs: [0]},
            'states': {stairs: {'weirdo_direction': 999, 'upside_down_bit': False}},
        }
        with self.assertRaisesRegex(ValueError, '方块状态不在当前版本表中'):
            merge_palette(document, source, (0, 0, 0), (1, 1, 1), (0, 0, 0))
        self.assertEqual(0, len(document.blocks))

    def test_palette_byte_state_text_resolves_without_coercing_numeric_or_bit_types(self):
        wall = ('minecraft:cobblestone_wall', 1)
        properties = states(wall)
        source = {
            'volume': (1, 1, 1),
            'common': {wall: [0]},
            'states': {wall: dict((key.encode('utf8'),
                                   value.encode('utf8') if isinstance(value, str) else value)
                                  for key, value in properties.items())},
        }
        document = Document((1, 1, 1))

        merge_palette(document, source, (0, 0, 0), (1, 1, 1), (0, 0, 0))

        self.assertEqual(wall, foreground(document.get((0, 0, 0))))

    def test_real_snowlogging_uses_snow_foreground_and_plant_background(self):
        snow = ('minecraft:snow_layer', 9)
        grass = ('minecraft:short_grass', 0)
        source = {
            'volume': (1, 1, 1),
            'common': {snow: [0]},
            'states': {snow: {'covered_bit': True, 'height': 1}},
            'extra': {grass: [0]},
            'extraStates': {grass: {}},
            'actor': {},
        }
        document = Document((1, 1, 1))

        merge_palette(document, source, (0, 0, 0), (1, 1, 1), (100, 64, 200))

        cell = document.get((0, 0, 0))
        self.assertEqual(snow, foreground(cell))
        self.assertEqual(grass, background(cell))
        self.assertIsNone(actor_data(cell))
        output = document.palette_data()
        self.assertEqual(source['common'], output['common'])
        self.assertEqual(source['extra'], output['extra'])

    def test_real_client_double_chest_actor_render_data_stays_independent(self):
        chest = ('minecraft:chest', 2)
        main = {'chestMainSubChest': True, 'chestModelOffset': 0.,
                'chestIsLargeChest': True, 'facingDirection': 2,
                'chestOpenness': 0., 'chestOldOpenness': 0.,
                'chestIsGlobalChest': False}
        secondary = dict(main, chestMainSubChest=False, chestModelOffset=-.5)
        source = {
            'volume': (1, 2, 1), 'common': {chest: [0, 1]},
            'states': {chest: states(chest)},
            'actor': {'minecraft:chest': {0: main, 1: secondary}},
        }
        document = Document((2, 1, 1))

        merge_palette(document, source, (0, 0, 0), (2, 1, 1), (100, 64, 200))

        self.assertEqual(main, actor_data(document.get((0, 0, 0))))
        self.assertEqual(secondary, actor_data(document.get((1, 0, 0))))
        output = document.palette_data()
        self.assertEqual(source['actor'], output['actor'])
        actor_data(document.get((0, 0, 0)))['chestModelOffset'] = 10.
        self.assertEqual(0., actor_data(document.get((0, 0, 0)))['chestModelOffset'])
        self.assertEqual(-.5, actor_data(document.get((1, 0, 0)))['chestModelOffset'])

    def test_capture_rejects_unloaded_or_unknown_chunk_edges(self):
        loaded = {(0, 0, 0), (0, 0, 1)}
        with self.assertRaisesRegex(ValueError, '未加载区块'):
            validate_loaded_chunk(loaded, 0, (15, 64, 0), (16, 65, 1),
                                  lambda pos: ('minecraft:air', 0))
        with self.assertRaisesRegex(ValueError, '尚未加载'):
            validate_loaded_chunk(loaded, 0, (0, 64, 0), (1, 65, 1),
                                  lambda pos: None if pos == (1, 65, 1) else ('minecraft:air', 0))


if __name__ == '__main__':
    unittest.main()
