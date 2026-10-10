import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_registry import from_states, states
from projection.cell import AIR, actor_data, background, edit_cell, foreground, make_cell

WATER = ('minecraft:water', 0)
FENCE = ('minecraft:oak_fence', 0)
STONE = ('minecraft:stone', 0)
PLANT = ('minecraft:short_grass', 0)
FERN = ('minecraft:fern', 0)
SNOW = ('minecraft:snow_layer', 2)


class CellEditTests(unittest.TestCase):
    def setUp(self):
        self.water = patch('projection.block_traits.is_waterloggable',
                           lambda material: material == FENCE, create=True)
        self.snow = patch('projection.block_traits.is_snow_coverable',
                          lambda material: material in (PLANT, FERN), create=True)
        self.water.start()
        self.snow.start()
        self.addCleanup(self.water.stop)
        self.addCleanup(self.snow.stop)

    def assert_layers(self, value, front, back=AIR):
        self.assertEqual(front, foreground(value))
        self.assertEqual(back, background(value))

    def covered(self, height=2):
        return from_states('minecraft:snow_layer', {'covered_bit': True, 'height': height})

    def test_water_composes_in_both_placement_orders(self):
        self.assert_layers(edit_cell(FENCE, WATER), FENCE, WATER)
        self.assert_layers(edit_cell(WATER, FENCE), FENCE, WATER)
        self.assert_layers(edit_cell(FENCE, WATER, 1), FENCE, WATER)

    def test_foreground_erasure_leaves_standalone_water(self):
        combined = make_cell(FENCE, WATER)
        self.assertEqual(WATER, edit_cell(combined, AIR))
        self.assertEqual(AIR, edit_cell(edit_cell(combined, AIR), AIR))
        self.assertEqual(FENCE, edit_cell(combined, AIR, 1))

    def test_plain_replacement_removes_only_incompatible_native_background(self):
        self.assertEqual(STONE, edit_cell(make_cell(FENCE, WATER), STONE))
        self.assert_layers(edit_cell(make_cell(FENCE, ('minecraft:glass', 0)), STONE),
                           STONE, ('minecraft:glass', 0))
        self.assert_layers(edit_cell(STONE, WATER, 1), STONE, WATER)

    def test_snow_composes_in_both_orders_with_native_layer_order(self):
        self.assert_layers(edit_cell(PLANT, SNOW), self.covered(), PLANT)
        self.assert_layers(edit_cell(SNOW, PLANT), self.covered(), PLANT)
        self.assert_layers(edit_cell(PLANT, SNOW, 1), self.covered(), PLANT)
        self.assert_layers(edit_cell(SNOW, PLANT, 1), self.covered(), PLANT)

    def test_snow_erasure_promotes_plant_and_plant_erasure_retains_uncovered_snow(self):
        combined = make_cell(self.covered(), PLANT)
        self.assertEqual(PLANT, edit_cell(combined, AIR))
        self.assertEqual(SNOW, edit_cell(combined, AIR, 1))
        self.assertEqual(AIR, edit_cell(edit_cell(combined, AIR, 1), AIR))

    def test_snow_and_plant_replacement_keep_height_and_cover_flag_in_sync(self):
        combined = make_cell(self.covered(), PLANT)
        self.assert_layers(edit_cell(combined, FERN), self.covered(), FERN)
        self.assert_layers(edit_cell(combined, ('minecraft:snow_layer', 7)),
                           self.covered(7), PLANT)
        self.assertEqual(STONE, edit_cell(combined, STONE))
        standalone = edit_cell(AIR, self.covered())
        self.assertEqual(SNOW, standalone)
        self.assertFalse(states(standalone)['covered_bit'])

    def test_water_background_edits_preserve_existing_actor(self):
        actor = {'render': {'chestOpenness': 0.0}, 'inventory': ['kept']}
        value = make_cell(FENCE, AIR, actor)
        result = edit_cell(value, WATER)
        self.assertEqual(actor, actor_data(result))
        self.assertEqual(actor, actor_data(edit_cell(result, AIR, 1)))
        self.assertIsNone(actor_data(edit_cell(result, AIR)))

    def test_invalid_layer_indexes_are_rejected(self):
        for index in (-1, 2, True, 1.0):
            with self.assertRaises(ValueError):
                edit_cell(FENCE, WATER, index)


if __name__ == '__main__':
    unittest.main()
