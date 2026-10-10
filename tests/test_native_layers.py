import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import canonical, states
from projection.cell import AIR, actor_data, background, foreground, make_cell
from projection.geometry_palette import prepare_palette
from projection.native_layers import native_cell, normalize_palette_layers


class NativeLayerTests(unittest.TestCase):
    def setUp(self):
        self.water = ('minecraft:water', 0)
        self.fence = ('minecraft:oak_fence', 0)
        self.grass = ('minecraft:short_grass', 0)
        self.snow = ('minecraft:snow_layer', 2)
        self.covered = ('minecraft:snow_layer', 10)
        self.stone = ('minecraft:stone', 0)
        handle = patch('projection.native_layers.is_waterloggable',
                       side_effect=lambda value: value in (
                           self.fence, ('minecraft:oak_slab', 1), ('minecraft:chest', 2)))
        handle.start()
        self.addCleanup(handle.stop)

    def test_world_and_palette_normalization_agree_for_all_native_layer_orders(self):
        cases = ((AIR, self.water), (AIR, self.grass), (AIR, self.covered),
                 (self.water, self.fence), (('minecraft:flowing_water', 1), self.fence),
                 (self.grass, self.snow), (self.covered, self.grass),
                 (self.covered, AIR), (self.covered, self.stone),
                 (self.water, self.stone), (self.water, ('minecraft:wooden_slab', 8)))
        for front, back in cases:
            with self.subTest(front=front, back=back):
                cell = make_cell(front, back)
                saved = (foreground(cell), background(cell), actor_data(cell))
                front, back = canonical(front), canonical(back)
                common = {} if front == AIR else {front: [0]}
                extra = {} if back == AIR else {back: [0]}
                common_states = dict((value, states(value)) for value in common)
                extra_states = dict((value, states(value)) for value in extra)
                normalize_palette_layers(common, common_states, extra, extra_states)
                result = native_cell(cell)
                expected_common = {} if foreground(result) == AIR else {foreground(result): [0]}
                expected_extra = {} if background(result) == AIR else {background(result): [0]}
                self.assertEqual(expected_common, common)
                self.assertEqual(expected_extra, extra)
                self.assertEqual(saved, (foreground(cell), background(cell), actor_data(cell)))

    def test_native_identity_is_reused_and_entity_data_is_preserved(self):
        actor = {'facingDirection': 2, 'chestIsLargeChest': True}
        cell = make_cell(('minecraft:chest', 2), self.water, actor)
        self.assertIs(cell, native_cell(cell))
        self.assertEqual(actor, actor_data(native_cell(cell)))
        alias = make_cell(('minecraft:wooden_slab', 8), self.water, actor)
        result = native_cell(alias)
        self.assertEqual(('minecraft:oak_slab', 1), foreground(result))
        self.assertEqual(actor, actor_data(result))
        self.assertEqual(('minecraft:wooden_slab', 8), foreground(alias))

    def test_world_normalization_never_uses_hidden_foliage_render_proxies(self):
        leaf = ('minecraft:oak_leaves', 3)
        cell = make_cell(leaf, self.water)
        saved = copy.deepcopy(cell)
        self.assertEqual(leaf, foreground(native_cell(cell)))
        rendered = prepare_palette({'common': {leaf: [0]}, 'extra': {self.water: [0]}})
        self.assertEqual({('modern_projection:preview_oak_leaves', 0): [0]}, rendered['common'])
        self.assertEqual(saved, cell)

    def test_unsupported_historical_layer_pairs_keep_both_original_materials(self):
        cell = make_cell(self.water, self.stone)
        self.assertIs(cell, native_cell(cell))
        self.assertEqual(self.stone, background(native_cell(cell)))


if __name__ == '__main__':
    unittest.main()
