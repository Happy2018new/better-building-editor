"""Native actor models retain local coordinates and emit only visible targets."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.block_registry import states
from projection.cell import actor_data, background, foreground, make_cell
from projection.debug_blueprints import build, material
from projection.entity_render import native_actor
from projection.model import Document
from projection.render_context import prepare_context_batches
from projection.render_layout import local_context_position


def context_index(target, neighbor=(0, 0, 0)):
    x, y, z = local_context_position(target, neighbor)
    return (y * 64 + x) * 64 + z


class NativeActorContextTests(unittest.TestCase):
    def test_native_sign_and_pot_emit_in_local_palette_once_across_chunk_boundary(self):
        for fixture, pos in (('test.entities.signs', (3, 1, 3)),
                             ('test.entities.pottery', (3, 1, 3))):
            value = build(fixture).get(pos)
            name = foreground(value)[0]
            doc = Document((32, 32, 32), {(15, 15, 15): value, (16, 15, 15): value})
            before = copy.deepcopy(doc.to_data())
            targets = doc.palette_data(lambda position: position == (16, 15, 15))
            prepared = prepare_context_batches(doc, targets)
            self.assertEqual(1, len(prepared['_context_batches']))
            origin, context, palette = prepared['_context_batches'][0]
            self.assertEqual((16, 0, 0), origin)
            self.assertFalse(context)
            self.assertEqual((16, 16, 16), palette['volume'])
            index = (15 * 16 + 0) * 16 + 15
            self.assertEqual([index], palette['common'][foreground(value)])
            self.assertEqual({index: native_actor(foreground(value), actor_data(value))},
                             palette['actor'][name])
            self.assertEqual(before, doc.to_data())

    def test_opaque_neighbor_and_wet_actor_preserve_separate_layer_coordinates(self):
        value = build('test.entities.signs').get((3, 1, 3))
        water = material('water')
        wet = make_cell(foreground(value), water, actor_data(value))
        doc = Document((4, 4, 4), {(1, 1, 1): wet, (1, 0, 1): material('stone')})
        before = copy.deepcopy(doc.to_data())
        data = prepare_context_batches(doc, doc.palette_data())
        self.assertEqual(2, len(data['_context_batches']))
        palettes = {context: palette for unused, context, palette in data['_context_batches']}
        self.assertNotIn(foreground(value), palettes[True]['common'])
        self.assertEqual({}, palettes[True]['actor'])
        index = (1 * 16 + 1) * 16 + 1
        self.assertEqual({}, palettes[False]['extra'])
        self.assertEqual({context_index((1, 1, 1)),
                          context_index((1, 0, 1), (0, 1, 0))},
                         set(palettes[True]['common'][water]))
        self.assertEqual({}, palettes[True]['extra'])
        self.assertEqual(states(water), palettes[True]['states'][water])
        self.assertEqual({}, palettes[True]['extraStates'])
        self.assertEqual([index], palettes[False]['common'][foreground(value)])
        self.assertEqual(before, doc.to_data())
        self.assertEqual(water, background(doc.get((1, 1, 1))))

    def test_hidden_wet_actor_across_chunk_promotes_only_its_own_water(self):
        actor_pos, target = (15, 15, 15), (16, 15, 15)
        water, fence = material('water'), material('oak_fence')
        for fixture in ('test.entities.signs', 'test.entities.pottery'):
            with self.subTest(fixture=fixture):
                value = build(fixture).get((3, 1, 3))
                doc = Document((32, 32, 32), {
                    actor_pos: make_cell(foreground(value), water, actor_data(value)),
                    target: make_cell(fence, water)})
                before = copy.deepcopy(doc.to_data())
                targets = doc.palette_data(lambda position: position == target)
                data = prepare_context_batches(doc, targets)
                self.assertEqual(1, len(data['_context_batches']))
                origin, context, palette = data['_context_batches'][0]
                self.assertEqual((16, 0, 0), origin)
                self.assertTrue(context)
                local_target = (0, 15, 15)
                self.assertEqual([context_index(local_target, (-1, 0, 0))],
                                 palette['common'][water])
                self.assertEqual([context_index(local_target)], palette['extra'][water])
                self.assertEqual([context_index(local_target)], palette['common'][fence])
                self.assertEqual(states(water), palette['states'][water])
                self.assertEqual(states(water), palette['extraStates'][water])
                self.assertEqual({}, palette['actor'])
                self.assertEqual(before, doc.to_data())

    def test_selected_actor_and_primary_water_merge_without_changing_logical_layers(self):
        actor_pos, neighbor_pos = (17, 20, 17), (18, 20, 17)
        water = ('minecraft:flowing_water', 1)
        for fixture in ('test.entities.signs', 'test.entities.pottery'):
            with self.subTest(fixture=fixture):
                value = build(fixture).get((3, 1, 3))
                doc = Document((32, 32, 32), {
                    actor_pos: make_cell(foreground(value), water, actor_data(value)),
                    neighbor_pos: water})
                before = copy.deepcopy(doc.to_data())
                targets = doc.palette_data(lambda position: position == actor_pos)
                data = prepare_context_batches(doc, targets)
                self.assertEqual(2, len(data['_context_batches']))
                palettes = {context: palette for unused, context, palette in data['_context_batches']}
                local_target = (1, 4, 1)
                self.assertEqual({context_index(local_target),
                                  context_index(local_target, (1, 0, 0))},
                                 set(palettes[True]['common'][water]))
                self.assertEqual({}, palettes[True]['extra'])
                self.assertEqual(states(water), palettes[True]['states'][water])
                self.assertEqual({}, palettes[True]['extraStates'])
                index = (4 * 16 + 1) * 16 + 1
                self.assertEqual({foreground(value): [index]}, palettes[False]['common'])
                self.assertEqual({}, palettes[False]['extra'])
                self.assertEqual(before, doc.to_data())
                self.assertEqual(water, background(doc.get(actor_pos)))


if __name__ == '__main__':
    unittest.main()
