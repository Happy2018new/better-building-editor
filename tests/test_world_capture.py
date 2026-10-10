"""Native client palette capture preserves both layers and block actors."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))

from projection.cell import AIR, actor_data, background, foreground
from projection.block_registry import states
from projection.model import Document
from projection.world_capture import merge_palette, validate_loaded_chunk


class WorldCaptureTests(unittest.TestCase):
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
