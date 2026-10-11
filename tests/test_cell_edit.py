import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_registry import from_states, states
from projection.cell import (AIR, actor_data, background, can_compose, edit_cell,
                             foreground, layer, make_cell)

WATER = ('minecraft:water', 0)
FENCE = ('minecraft:oak_fence', 0)
STONE = ('minecraft:stone', 0)
PLANT = ('minecraft:short_grass', 0)
FERN = ('minecraft:fern', 0)
SNOW = ('minecraft:snow_layer', 2)


class CellEditTests(unittest.TestCase):
    def setUp(self):
        self.snow = patch('projection.block_traits.is_snow_coverable',
                          lambda material: material in (PLANT, FERN), create=True)
        self.snow.start()
        self.addCleanup(self.snow.stop)
        self.water = patch('projection.block_traits.is_waterloggable',
                           lambda material: material == FENCE, create=True)
        self.water.start()
        self.addCleanup(self.water.stop)

    def assert_layers(self, value, front, back=AIR):
        self.assertEqual(front, foreground(value))
        self.assertEqual(back, background(value))

    def covered(self, height=2):
        return from_states('minecraft:snow_layer', {'covered_bit': True, 'height': height})

    def test_water_placement_changes_only_the_selected_layer(self):
        self.assertEqual(WATER, edit_cell(FENCE, WATER))
        self.assertEqual(FENCE, edit_cell(WATER, FENCE))
        self.assert_layers(edit_cell(FENCE, WATER, 1), FENCE, WATER)
        self.assert_layers(edit_cell(make_cell(AIR, WATER), FENCE), FENCE, WATER)

    def test_erasure_never_promotes_the_other_layer_in_document_data(self):
        combined = make_cell(FENCE, WATER)
        self.assert_layers(edit_cell(combined, AIR), AIR, WATER)
        self.assertEqual(FENCE, edit_cell(combined, AIR, 1))
        self.assertEqual(AIR, edit_cell(edit_cell(combined, AIR), AIR, 1))

    def test_replacement_keeps_background_even_for_legacy_arbitrary_combinations(self):
        self.assert_layers(edit_cell(make_cell(FENCE, WATER), STONE), STONE, WATER)
        self.assert_layers(edit_cell(STONE, WATER, 1), STONE, WATER)

    def test_snow_placement_never_swaps_the_user_selected_layers(self):
        self.assertEqual(SNOW, edit_cell(PLANT, SNOW))
        self.assertEqual(PLANT, edit_cell(SNOW, PLANT))
        self.assert_layers(edit_cell(PLANT, SNOW, 1), PLANT, SNOW)
        self.assert_layers(edit_cell(SNOW, PLANT, 1), SNOW, PLANT)

    def test_each_snow_layer_erases_independently(self):
        combined = make_cell(self.covered(), PLANT)
        self.assert_layers(edit_cell(combined, AIR), AIR, PLANT)
        self.assertEqual(self.covered(), edit_cell(combined, AIR, 1))
        self.assertEqual(AIR, edit_cell(edit_cell(combined, AIR, 1), AIR))

    def test_explicit_snow_state_is_preserved_and_native_flags_are_derived_temporarily(self):
        from projection.native_layers import native_cell
        combined = make_cell(self.covered(), PLANT)
        self.assert_layers(edit_cell(combined, FERN, 1), self.covered(), FERN)
        requested = ('minecraft:snow_layer', 7)
        edited = edit_cell(combined, requested)
        self.assert_layers(edited, requested, PLANT)
        self.assert_layers(native_cell(edited), self.covered(7), PLANT)
        self.assert_layers(edited, requested, PLANT)
        self.assert_layers(edit_cell(combined, STONE), STONE, PLANT)
        standalone = edit_cell(AIR, self.covered())
        self.assertEqual(self.covered(), standalone)
        self.assertTrue(states(standalone)['covered_bit'])
        self.assertEqual(SNOW, native_cell(standalone))
        self.assertEqual(self.covered(), standalone)

    def test_explicit_background_snow_edits_leave_foreground_and_actor_unchanged(self):
        actor = {'source': 'foreground', 'nested': [1, 2]}
        for front, back in ((SNOW, AIR), (self.covered(), PLANT)):
            before = make_cell(front, back, actor)
            for replacement in (PLANT, FERN, STONE, AIR):
                with self.subTest(front=front, back=back, replacement=replacement):
                    after = edit_cell(before, replacement, 1)
                    self.assertEqual(front, foreground(after))
                    self.assertEqual(actor, actor_data(after))
                    self.assertEqual(replacement, background(after))

    def test_background_snow_edits_and_history_preserve_the_unselected_layer(self):
        from projection.model import Document, Editor
        from projection.native_layers import native_cell
        for front, back, replacement in ((SNOW, AIR, PLANT), (self.covered(), PLANT, AIR)):
            with self.subTest(front=front, back=back):
                position = (1, 1, 1)
                before = make_cell(front, back)
                editor = Editor(Document((3, 3, 3), {position: before}))
                editor.edit_layer = 1
                editor.material = replacement
                editor.paint_at(position, respect_selection=False)
                after = editor.document.get(position)
                self.assert_layers(after, front, replacement)
                native = native_cell(after)
                self.assertEqual(replacement != AIR, states(foreground(native))['covered_bit'])
                self.assertEqual(after, editor.document.get(position))
                self.assertTrue(editor.undo())
                self.assertEqual(before, editor.document.get(position))
                self.assertTrue(editor.redo())
                self.assertEqual(after, editor.document.get(position))

    def test_background_edits_preserve_existing_actor(self):
        actor = {'render': {'chestOpenness': 0.0}, 'inventory': ['kept']}
        value = make_cell(FENCE, AIR, actor)
        result = edit_cell(value, WATER, 1)
        self.assertEqual(actor, actor_data(result))
        self.assertEqual(actor, actor_data(edit_cell(result, AIR, 1)))
        self.assertIsNone(actor_data(edit_cell(result, AIR)))

    def test_invalid_layer_indexes_are_rejected(self):
        for index in (-1, 3, True, 1.0):
            with self.assertRaises(ValueError):
                edit_cell(FENCE, WATER, index)

    def test_automatic_water_placement_supports_both_orders_and_erase_priority(self):
        combined = make_cell(FENCE, WATER)
        self.assertEqual(combined, edit_cell(FENCE, WATER, 2))
        self.assertEqual(combined, edit_cell(WATER, FENCE, 2))
        self.assertEqual(WATER, edit_cell(combined, AIR, 2))
        self.assertEqual(AIR, edit_cell(edit_cell(combined, AIR, 2), AIR, 2))
        self.assertEqual(STONE, edit_cell(combined, STONE, 2))

    def test_automatic_snow_placement_supports_both_orders_and_erase_priority(self):
        combined = make_cell(self.covered(), PLANT)
        self.assertEqual(combined, edit_cell(PLANT, SNOW, 2))
        self.assertEqual(combined, edit_cell(SNOW, PLANT, 2))
        self.assertEqual(PLANT, edit_cell(combined, AIR, 2))
        self.assertEqual(STONE, edit_cell(combined, STONE, 2))

    def test_automatic_erasure_preserves_imported_background_without_capability_queries(self):
        for front, back in ((self.covered(), ('minecraft:tall_grass', 0)),
                            (STONE, FERN), (FENCE, WATER)):
            with self.subTest(front=front, back=back), \
                    patch('projection.block_traits.is_snow_coverable',
                          side_effect=AssertionError('erasure does not validate placement')), \
                    patch('projection.block_traits.is_waterloggable',
                          side_effect=AssertionError('erasure does not validate placement')):
                combined = make_cell(front, back, {'source': 'foreground'})
                result = edit_cell(combined, AIR, 2)
                self.assertEqual(back, result)
                self.assertIsNone(actor_data(result))
                self.assertEqual(AIR, edit_cell(result, AIR, 2))

    def test_automatic_mode_handles_background_only_cells_without_extra_steps(self):
        self.assertEqual(make_cell(FENCE, WATER), edit_cell(make_cell(AIR, WATER), FENCE, 2))
        self.assertEqual(make_cell(self.covered(), PLANT), edit_cell(make_cell(AIR, PLANT), SNOW, 2))
        self.assertEqual(AIR, edit_cell(make_cell(AIR, WATER), AIR, 2))
        self.assertEqual(AIR, edit_cell(make_cell(AIR, PLANT), AIR, 2))

    def test_automatic_picker_uses_foreground_before_background(self):
        self.assertEqual(FENCE, layer(make_cell(FENCE, WATER), 2))
        self.assertEqual(WATER, layer(make_cell(AIR, WATER), 2))
        self.assertEqual(AIR, layer(AIR, 2))

    def test_automatic_placement_targets_existing_cells_only_for_native_composition(self):
        for before, material in ((FENCE, WATER), (WATER, FENCE),
                                 (PLANT, SNOW), (SNOW, PLANT),
                                 (make_cell(self.covered(), PLANT), SNOW),
                                 (make_cell(AIR, WATER), FENCE),
                                 (make_cell(AIR, PLANT), SNOW)):
            self.assertTrue(can_compose(before, material), (before, material))
        for before, material in ((AIR, WATER), (STONE, WATER), (FENCE, STONE),
                                 (FENCE, SNOW), (SNOW, FENCE),
                                 (make_cell(FENCE, WATER), FENCE)):
            self.assertFalse(can_compose(before, material), (before, material))


if __name__ == '__main__':
    unittest.main()
