"""Shelf body replacement preserves context ownership and original slot data."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'), str(ROOT/'behavior_pack/modern_projection')]
from projection import shelf_body
from projection.block_registry import aux_values, states
from projection.cell import actor_data, make_cell
from projection.debug_item_blueprints import slot_observations
from projection.geometry_palette import INTERNAL_RENDER_BLOCKS, prepare_palette
from projection.item_sprite_plan import iter_render_steps
from projection.item_sprite_profile import ItemSpriteProfile, shelf_candidate_profile
from projection.model import Document
from projection.render_context import prepare_context_batches
from projection.render_layout import local_context_center, native_mesh_position
from projection.visible_actor import compose_actor
from projection.visible_item_contents import content_slots


SOURCE = ('minecraft:oak_shelf', 0)
PROXY = (shelf_body.identifier('oak', 'unpowered', 'south'), 0)


def centers(palette):
    width, depth, unused = palette['volume']
    return {index for positions in palette['common'].values() for index in positions
            if local_context_center(native_mesh_position((index//width % depth + .5,
                index//(width*depth) + .5, index % width + .5)))}


def slot_actor():
    row = next(row for row in slot_observations() if row['name'] == SOURCE[0])
    actor = copy.deepcopy(row['after'])
    enchanted = copy.deepcopy(actor['Items'][1])
    plain = copy.deepcopy(enchanted)
    del plain['tag']
    apple = copy.deepcopy(plain)
    apple['Name']['__value__'] = 'minecraft:apple'
    actor['Items'] = [apple, plain, enchanted]
    return compose_actor({}, actor)


class ShelfBodyProductTests(unittest.TestCase):
    def setUp(self):
        self.enabled = patch.object(shelf_body, 'BODY_ENABLED', True)
        self.enabled.start()
        self.addCleanup(self.enabled.stop)

    def test_all_observed_semantic_states_have_registered_models_and_original_texels(self):
        blocks = json.loads((ROOT/'resource_pack/blocks.json').read_bytes())
        count, models = 0, set()
        for name in shelf_body.SHELF_NAMES:
            self.assertEqual(32, len(aux_values(name)))
            for aux in aux_values(name):
                material = (name, aux)
                record = states(material)
                proxy = shelf_body.body_proxy(material, record)
                self.assertIsNotNone(proxy)
                models.add(proxy[0])
                self.assertIn(proxy[0], INTERNAL_RENDER_BLOCKS)
                self.assertEqual(proxy[0], blocks[proxy[0]]['netease_model'])
                count += 1
        self.assertEqual(384, count)
        self.assertEqual(240, len(models))
        for model in models:
            stem = model.split(':', 1)[1]
            data = json.loads((ROOT/('resource_pack/models/netease_block/'+stem+'.json')).read_bytes())
            geometry = data['netease:block_geometry']
            self.assertEqual(model, geometry['description']['identifier'])
            self.assertTrue(geometry['description']['use_ao'])
            self.assertEqual(5, len(geometry['bones'][0]['cubes']))
            self.assertTrue(all(all(value > 0 for value in cube['size'])
                                for cube in geometry['bones'][0]['cubes']))

    def test_powered_role_mapping_uses_observed_roles(self):
        for aux, front in ((0, 'unpowered'), (1, 'unpowered'), (4, 'unconnected'),
                           (5, 'right'), (6, 'center'), (7, 'left')):
            self.assertEqual((shelf_body.identifier('oak', front, 'south'), 0),
                             shelf_body.body_proxy((SOURCE[0], aux), states((SOURCE[0], aux))))

    def test_contents_are_limited_to_the_body_and_measured_orientation(self):
        self.assertTrue(shelf_body.accepts_item_contents(SOURCE, slot_actor()))
        for material in ((SOURCE[0], 1), (SOURCE[0], 8), ('minecraft:birch_shelf', 0)):
            self.assertFalse(shelf_body.accepts_item_contents(material, slot_actor()))
        with patch.object(shelf_body, 'BODY_ENABLED', False):
            self.assertFalse(shelf_body.accepts_item_contents(SOURCE, slot_actor()))

    def test_conflicting_or_wrongly_typed_states_do_not_replace(self):
        expected = states(SOURCE)
        for record in (dict(expected, powered_bit=0), dict(expected, powered_shelf_type=False),
                       dict(expected, powered_shelf_type=1),
                       dict(expected, **{'minecraft:cardinal_direction': 'north'}),
                       {'powered_bit': False}, dict(expected, unknown=1)):
            self.assertIsNone(shelf_body.body_proxy(SOURCE, record))
            source = {'common': {SOURCE: [0]}, 'states': {SOURCE: record}}
            self.assertEqual([0], prepare_palette(source)['common'][SOURCE])
        self.assertEqual(PROXY, shelf_body.body_proxy(SOURCE, {}))
        self.assertEqual(PROXY, shelf_body.body_proxy(SOURCE, None))

    def test_scene_body_source_document_and_three_slot_item_plans(self):
        actor = slot_actor()
        document = Document((1, 2, 1), {(0, 0, 0): ('minecraft:cyan_concrete', 0),
                                      (0, 1, 0): make_cell(SOURCE, nbt=actor)})
        original = copy.deepcopy(document.to_data())
        prepared = prepare_palette(document.palette_data())
        self.assertEqual([1], prepared['common'][PROXY])
        self.assertEqual([0], prepared['common'][('minecraft:cyan_concrete', 0)])
        self.assertNotIn(SOURCE, prepared['states'])
        self.assertEqual({}, prepared['actor'])
        profile = ItemSpriteProfile(shelf_body.ENGINE_VERSION, include_frame_blocks=False)
        profile.content_families = ('shelf',)
        steps = tuple(step for step in iter_render_steps(document, profile) if step is not None)
        self.assertEqual(2, len(steps))
        self.assertEqual(3, sum(int(step.uniforms[3][1]) for step in steps))
        self.assertEqual((0, 1, 2), tuple(slot.index for slot in content_slots(
            SOURCE, actor_data(document.get((0, 1, 0))), shelf_body.ENGINE_VERSION)))
        self.assertEqual(original, document.to_data())

    def test_original_four_direction_geometry_is_used_instead_of_failed_baked_controls(self):
        base = ROOT/'docs/evidence/shelf-direction-r21-v1/candidate-inputs/resource_pack'
        for direction in shelf_body.DIRECTIONS:
            old = json.loads((base/('models/netease_block/preview_shelf_oak_unpowered_'+direction+'_ao.json')).read_bytes())
            new = json.loads((ROOT/('resource_pack/models/netease_block/preview_shelf_oak_unpowered_'+direction+'_body.json')).read_bytes())
            old['netease:block_geometry']['description'].pop('identifier')
            new['netease:block_geometry']['description'].pop('identifier')
            self.assertEqual(old, new)
        texture = 'textures/blocks/modern_projection_shelf_oak.png'
        self.assertEqual((base/texture).read_bytes(), (ROOT/'resource_pack'/texture).read_bytes())

    def test_real_narrow_item_factory_renders_exact_three_slots_with_body_gate(self):
        document = Document((1, 1, 1), {(0, 0, 0): make_cell(SOURCE, nbt=slot_actor())})
        profile = shelf_candidate_profile(shelf_body.ENGINE_VERSION)
        self.assertEqual(('shelf',), profile.content_families)
        self.assertEqual({('minecraft:apple', 0), ('minecraft:diamond_sword', 0)}, set(profile.items))
        rendered = tuple(step for step in iter_render_steps(document, profile) if step is not None)
        self.assertEqual(2, len(rendered))
        self.assertEqual(3, sum(int(step.uniforms[3][1]) for step in rendered))
        with patch.object(shelf_body, 'BODY_ENABLED', False):
            self.assertEqual((), tuple(step for step in iter_render_steps(document, profile) if step is not None))

    def test_full_missing_neighbor_and_hidden_layer_context_centers(self):
        target, occupied, hidden = (0, 1, 0), (1, 1, 0), (0, 2, 0)
        document = Document((2, 3, 1), {target: make_cell(SOURCE, nbt=slot_actor()),
                                      occupied: make_cell(SOURCE, nbt=slot_actor()), hidden: SOURCE})
        before = copy.deepcopy(document.to_data())
        for visible in (lambda pos: pos[1] == 1, lambda pos: pos == target):
            targets = document.palette_data(visible)
            with patch.object(shelf_body, 'BODY_ENABLED', False):
                native = prepare_context_batches(document, targets, visible_layer=lambda y: y != 2)
            result = prepare_context_batches(document, targets, visible_layer=lambda y: y != 2)
            self.assertEqual(len(native['_context_batches']), len(result['_context_batches']))
            for old, new in zip(native['_context_batches'], result['_context_batches']):
                self.assertEqual(old[:2], new[:2])
                self.assertEqual(old[2]['volume'], new[2]['volume'])
                self.assertEqual(old[2]['common'][SOURCE], new[2]['common'][PROXY])
                self.assertEqual(centers(old[2]), centers(new[2]))
                self.assertEqual({}, new[2]['actor'])
            profile = ItemSpriteProfile(shelf_body.ENGINE_VERSION, include_frame_blocks=False)
            profile.content_families = ('shelf',)
            steps = tuple(step for step in iter_render_steps(document, profile, visible=visible)
                          if step is not None)
            self.assertEqual(6 if visible(occupied) else 3,
                             sum(int(step.uniforms[3][1]) for step in steps))
        self.assertEqual(before, document.to_data())

    def test_other_actor_names_same_index_and_second_layer_are_unchanged(self):
        water = ('minecraft:water', 0)
        source = {'common': {SOURCE: [1]}, 'volume': (1, 1, 2),
                  'extra': {water: [1]}, 'extraStates': {water: {'liquid_depth': 0}},
                  'actor': {SOURCE[0]: {1: slot_actor(), 0: slot_actor()},
                            'minecraft:campfire': {1: {'id': 'Campfire'}}}, 'custom': (1, 2)}
        before = copy.deepcopy(source)
        prepared = prepare_palette(source)
        self.assertNotIn(1, prepared['actor'][SOURCE[0]])
        self.assertIn(0, prepared['actor'][SOURCE[0]])
        self.assertIn('minecraft:campfire', prepared['actor'])
        self.assertEqual(before, source)
        for key in ('extra', 'extraStates', 'volume', 'custom'):
            self.assertEqual(source[key], prepared[key])

    def test_bookshelf_chiseled_bookshelf_lectern_and_table_result_unchanged(self):
        for name in ('minecraft:bookshelf', 'minecraft:chiseled_bookshelf',
                     'minecraft:lectern', 'minecraft:enchanting_table'):
            material = (name, 0)
            source = {'common': {material: [0]}, 'volume': (1, 1, 1),
                      'actor': {name: {0: {'id': name}}}}
            with patch.object(shelf_body, 'BODY_ENABLED', False):
                before = prepare_palette(source)
            self.assertEqual(before, prepare_palette(source))


if __name__ == '__main__':
    unittest.main()
