"""The candidate must retain document neighbors and packed target ownership."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'behavior_pack/modern_projection')]
from shelf_render_palette_candidate_r21 import SOURCE, PROXY, replace_body_palette
from projection.cell import AIR, actor_data, make_cell
from projection.debug_item_blueprints import slot_observations
from projection.item_sprite_plan import iter_render_steps
from projection.item_sprite_profile import candidate_profile
from projection.model import Document
from projection.geometry_palette import prepare_palette
from projection.render_context import prepare_context_batches
from projection.render_layout import local_context_center, native_mesh_position
from projection.visible_actor import compose_actor
from projection.visible_item_contents import content_slots, ENGINE_VERSION


def visible_centers(palette):
    volume = palette['volume']
    return {index for entries in palette['common'].values() for index in entries
            if local_context_center(native_mesh_position((index // volume[0] % volume[1] + .5,
                index // (volume[0]*volume[1]) + .5, index % volume[0] + .5)))}


class ShelfRenderPaletteCandidateTests(unittest.TestCase):
    def document(self):
        return Document((1, 2, 1), {(0, 0, 0): ('minecraft:cyan_concrete', 0),
            (0, 1, 0): make_cell(SOURCE, AIR, {'Items': []})})

    def test_full_main_palette_replaces_only_body_and_keeps_support(self):
        document = self.document()
        original = copy.deepcopy(document.to_data())
        prepared = prepare_palette(document.palette_data())
        before = copy.deepcopy(prepared)
        result = replace_body_palette(prepared)
        self.assertEqual([0], result['common'][('minecraft:cyan_concrete', 0)])
        self.assertEqual([1], result['common'][PROXY])
        self.assertNotIn(SOURCE, result['common'])
        self.assertEqual((1, 1, 2), result['volume'])
        self.assertEqual({}, result['actor'])
        self.assertEqual(before, prepared)
        self.assertEqual(original, document.to_data())
        self.assertEqual({'Items': []}, actor_data(document.get((0, 1, 0))))

    def test_full_and_missing_packed_context_indices_and_neighbors_stay_identical(self):
        for missing in (False, True):
            with self.subTest(missing=missing):
                document = self.document()
                targets = document.palette_data((lambda position: position[1] == 1) if missing else None)
                prepared = prepare_context_batches(document, targets)
                before = copy.deepcopy(prepared)
                result = replace_body_palette(prepared)
                self.assertEqual(before, prepared)
                self.assertEqual(prepared['volume'], result['volume'])
                self.assertEqual(prepared['_context_schema'], result['_context_schema'])
                self.assertEqual(len(prepared['_context_batches']), len(result['_context_batches']))
                for old, new in zip(prepared['_context_batches'], result['_context_batches']):
                    self.assertEqual(old[:2], new[:2])
                    old_palette, new_palette = old[2], new[2]
                    self.assertTrue(new[1])
                    self.assertEqual(old_palette['volume'], new_palette['volume'])
                    self.assertEqual(old_palette['common'][SOURCE], new_palette['common'][PROXY])
                    self.assertEqual(old_palette['common'][('minecraft:cyan_concrete', 0)],
                                     new_palette['common'][('minecraft:cyan_concrete', 0)])
                    self.assertNotIn(SOURCE, new_palette['common'])
                    self.assertEqual(old_palette['extra'], new_palette['extra'])

    def test_non_candidate_wood_direction_and_state_are_not_replaced(self):
        for material in (('minecraft:oak_shelf', 8), ('minecraft:oak_shelf', 1),
                         ('minecraft:birch_shelf', 0)):
            source = {'volume': (1, 1, 1), 'common': {material: [0]}, 'extra': {}, 'actor': {}}
            self.assertIs(source, replace_body_palette(source))

    def test_only_replaced_actor_cells_are_suppressed(self):
        source = {'volume': (1, 1, 3), 'common': {SOURCE: [1]},
                  'actor': {'minecraft:oak_shelf': {1: {'Items': []}, 2: {'Items': [1]}},
                            'minecraft:campfire': {1: {'id': 'Campfire'}},
                            b'minecraft:oak_shelf': {1: {'Items': []}, 2: {'Items': [2]}}}}
        self.assertEqual({'minecraft:oak_shelf': {2: {'Items': [1]}},
                          'minecraft:campfire': {1: {'id': 'Campfire'}},
                          b'minecraft:oak_shelf': {2: {'Items': [2]}}},
                         replace_body_palette(source)['actor'])
        self.assertEqual([1], replace_body_palette(source)['common'][PROXY])

    def test_second_layer_and_its_states_and_metadata_are_unchanged(self):
        water = ('minecraft:water', 0)
        source = {'volume': (1, 1, 2), 'common': {SOURCE: [1]}, 'extra': {water: [1]},
                  'states': {SOURCE: {'minecraft:cardinal_direction': 'south',
                                      'powered_bit': False, 'powered_shelf_type': 0}},
                  'extraStates': {water: {'liquid_depth': 0}}, 'actor': {},
                  'void': False, 'eliminateAir': True, '_private': ('keep', 7)}
        before = copy.deepcopy(source)
        result = replace_body_palette(source)
        self.assertEqual({}, result['states'])
        for key in ('extra', 'extraStates', 'volume', 'void', 'eliminateAir', '_private'):
            self.assertEqual(before[key], result[key])
        self.assertEqual(before, source)

    def test_occupied_neighbor_remains_context_only_and_never_becomes_a_target(self):
        target, occupied = (0, 1, 0), (1, 1, 0)
        document = Document((2, 2, 1), {target: SOURCE, occupied: SOURCE})
        prepared = prepare_context_batches(document, document.palette_data(lambda pos: pos == target))
        result = replace_body_palette(prepared)
        self.assertEqual(1, len(result['_context_batches']))
        old, new = prepared['_context_batches'][0], result['_context_batches'][0]
        self.assertEqual(old[:2], new[:2])
        self.assertTrue(new[1])
        self.assertEqual([20545, 20609], new[2]['common'][PROXY])
        self.assertEqual(visible_centers(old[2]), visible_centers(new[2]))
        self.assertEqual({20545}, visible_centers(new[2]))

    def test_hidden_layer_neighbors_are_not_reintroduced(self):
        target, hidden = (0, 1, 0), (0, 2, 0)
        document = Document((1, 3, 1), {target: SOURCE, hidden: SOURCE})
        prepared = prepare_context_batches(document, document.palette_data(lambda pos: pos == target),
                                           visible_layer=lambda y: y != 2)
        result = replace_body_palette(prepared)
        self.assertEqual(1, len(result['_context_batches']))
        palette = result['_context_batches'][0][2]
        self.assertEqual([20545], palette['common'][PROXY])
        self.assertEqual({20545}, visible_centers(palette))

    def test_original_document_retains_three_slot_items_and_target_only_plan(self):
        row = next(row for row in slot_observations() if row['name'] == SOURCE[0])
        nbt = copy.deepcopy(row['after'])
        nbt['Items'] = [copy.deepcopy(nbt['Items'][1]) for unused in range(3)]
        cell = make_cell(SOURCE, nbt=compose_actor({}, nbt))
        target, occupied = (0, 1, 0), (1, 1, 0)
        document = Document((2, 2, 1), {target: cell, occupied: cell})
        original = copy.deepcopy(document.to_data())
        visible = lambda pos: pos == target
        before = tuple(item for item in iter_render_steps(document, candidate_profile(ENGINE_VERSION),
                                                         visible=visible) if item is not None)
        result = replace_body_palette(prepare_context_batches(document, document.palette_data(visible)))
        self.assertEqual({}, result['_context_batches'][0][2]['actor'])
        self.assertEqual((0, 1, 2), tuple(slot.index for slot in content_slots(
            SOURCE, actor_data(document.get(target)), ENGINE_VERSION)))
        after = tuple(item for item in iter_render_steps(document, candidate_profile(ENGINE_VERSION),
                                                        visible=visible) if item is not None)
        self.assertEqual(before, after)
        self.assertEqual(1, len(after))
        self.assertEqual((1., 2., 3., 0.), after[0].uniforms[1])
        self.assertEqual(3., after[0].uniforms[3][1])
        self.assertEqual(original, document.to_data())


if __name__ == '__main__':
    unittest.main()
