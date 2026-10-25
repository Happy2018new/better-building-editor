"""Whole-building projection transforms preserve source and native semantics."""
import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))

from projection import block_registry as registry
from projection.block_groups import actor_pair_position, group_partner
from projection.cell import AIR, actor_data, background, foreground, make_cell
from projection.debug_blueprints import material
from projection.debug_transform_acceptance import build, PREFIX
from projection.model import Document
from projection.nbt_spatial import root_payload, scalar
from projection.projection_transform import (
    OPERATIONS, iter_snapshot, snapshot, transform_position, transform_size,
    validate_operations)
from projection.visible_actor import compose_actor, entity_nbt, render_actor


MATRICES = {
    'rotate_y90': ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
    'rotate_y180': ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
    'rotate_y270': ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
    'mirror_x': ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),
    'mirror_y': ((1, 0, 0), (0, -1, 0), (0, 0, 1)),
    'mirror_z': ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
}
INVERSES = {'rotate_y90': 'rotate_y270', 'rotate_y180': 'rotate_y180',
            'rotate_y270': 'rotate_y90', 'mirror_x': 'mirror_x',
            'mirror_y': 'mirror_y', 'mirror_z': 'mirror_z'}


def expected_point(position, size, operation):
    matrix = MATRICES[operation]
    def vector(point):
        return tuple(sum(matrix[axis][index] * point[index] for index in range(3))
                     for axis in range(3))
    corners = [vector(point) for point in itertools.product(
        *[(0, extent - 1) for extent in size])]
    minimum = tuple(min(point[axis] for point in corners) for axis in range(3))
    maximum = tuple(max(point[axis] for point in corners) for axis in range(3))
    result = vector(position)
    return (tuple(result[axis] - minimum[axis] for axis in range(3)),
            tuple(maximum[axis] - minimum[axis] + 1 for axis in range(3)))


def non_symmetric():
    return Document((7, 5, 3), {
        (0, 0, 0): material('red_concrete'),
        (6, 0, 0): material('lime_concrete'),
        (0, 4, 2): material('blue_concrete'),
        (5, 2, 1): material('dispenser', {'facing_direction': 5}),
        (1, 3, 2): material('oak_stairs', {'weirdo_direction': 0,
                                        'upside_down_bit': False}),
    }, name='projection-source', biome='desert')


class ProjectionTransformTests(unittest.TestCase):
    def test_all_six_map_every_cell_and_resize_using_independent_matrices(self):
        source = non_symmetric()
        before = source.to_data()
        for operation in OPERATIONS:
            with self.subTest(operation=operation):
                result = snapshot(source, (operation,))
                for position, value in source.blocks.items():
                    target, size = expected_point(position, source.size, operation)
                    self.assertEqual(size, result.size)
                    self.assertEqual(target, transform_position(position, source.size, (operation,)))
                    self.assertEqual(foreground(value)[0], foreground(result.get(target))[0])
                self.assertEqual(len(source.blocks), len(result.blocks))
                self.assertEqual(source.name, result.name)
                self.assertEqual(source.biome, result.biome)
                self.assertEqual(before, source.to_data())
                restored = snapshot(result, (INVERSES[operation],))
                self.assertEqual(source.size, restored.size)
                self.assertEqual(source.blocks, restored.blocks)

    def test_literal_direction_and_upper_lower_states_follow_native_rules(self):
        source = non_symmetric()
        rotated = snapshot(source, ('rotate_y90',))
        dispenser = rotated.get((1, 2, 5))
        self.assertEqual(3, registry.states(dispenser)['facing_direction'])
        stairs = rotated.get((0, 3, 1))
        self.assertEqual(2, registry.states(stairs)['weirdo_direction'])
        mirrored = snapshot(source, ('mirror_y',))
        self.assertTrue(registry.states(mirrored.get((1, 1, 2)))['upside_down_bit'])

    def test_identity_is_detached_and_copy_on_write_in_both_directions(self):
        source = non_symmetric()
        result = snapshot(source)
        self.assertIsNot(source, result)
        self.assertIsNot(source.blocks, result.blocks)
        self.assertEqual(source.blocks, result.blocks)
        old = result.get((0, 0, 0))
        source.set_cell((0, 0, 0), material('stone'))
        self.assertEqual(old, result.get((0, 0, 0)))
        original = source.get((6, 0, 0))
        result.set_cell((6, 0, 0), material('diamond_block'))
        self.assertEqual(original, source.get((6, 0, 0)))

    def test_iterator_captures_blocks_metadata_and_mutable_operations_at_call(self):
        source = non_symmetric()
        before = source.to_data()
        operations = ['rotate_y90', 'mirror_z']
        steps = iter_snapshot(source, operations)
        source.set_cell((0, 0, 0), material('stone'))
        source.name, source.biome = 'changed', 'plains'
        operations[:] = ['mirror_x']
        yielded = list(steps)
        self.assertEqual([None] * len(Document.from_data(before).blocks), yielded[:-1])
        expected = snapshot(Document.from_data(before), ('rotate_y90', 'mirror_z'))
        self.assertEqual(expected.to_data(), yielded[-1].to_data())

    def test_abandoning_iterator_does_not_publish_or_mutate_draft(self):
        source = non_symmetric()
        before = source.to_data()
        steps = iter_snapshot(source, ('mirror_x',))
        self.assertIsNone(next(steps))
        steps.close()
        self.assertEqual(before, source.to_data())

    def test_ordered_composition_matches_successive_native_semantics(self):
        source = non_symmetric()
        operations = ('rotate_y90', 'mirror_x', 'mirror_y', 'mirror_z')
        successive = source
        for operation in operations:
            successive = snapshot(successive, (operation,))
        result = snapshot(source, operations)
        self.assertEqual(successive.size, result.size)
        self.assertEqual(successive.blocks, result.blocks)
        self.assertNotEqual(snapshot(source, ('mirror_x', 'rotate_y90')).blocks,
                            snapshot(source, ('rotate_y90', 'mirror_x')).blocks)
        self.assertEqual((3, 5, 7), transform_size(source.size, operations))
        self.assertEqual((7, 5, 3), transform_size(source.size, ('rotate_y90',) * 4))

    def test_layered_typed_actor_coordinates_and_opaque_inventory_are_preserved(self):
        position = (5, 2, 1)
        front = material('chest', {'minecraft:cardinal_direction': 'north'})
        back = material('water')
        inventory = [{'Slot': {'__type__': 1, '__value__': 0},
                      'tag': {'x': 900, 'pairx': 901, 'custom': b'untouched'}}]
        typed = {'__type__': 10, '__value__': {
            'id': {'__type__': 8, '__value__': 'Chest'},
            'x': {'__type__': 3, '__value__': 5},
            'y': {'__type__': 3, '__value__': 2},
            'z': {'__type__': 3, '__value__': 1},
            'pairx': {'__type__': 3, '__value__': 6},
            'pairz': {'__type__': 3, '__value__': 1},
            'Items': inventory}}
        render = {'facingDirection': 2, 'chestIsLargeChest': True,
                  'chestMainSubChest': True, 'chestModelOffset': 0.0}
        value = make_cell(front, back, compose_actor(render, typed))
        source = Document((7, 5, 3), {position: value})
        before = source.to_data()
        result = snapshot(source, ('rotate_y90',))
        cell = result.get((1, 2, 5))
        self.assertEqual(back, background(cell))
        self.assertEqual('east', registry.states(foreground(cell))['minecraft:cardinal_direction'])
        root = root_payload(entity_nbt(actor_data(cell)))
        self.assertEqual((1, 2, 5), tuple(scalar(root, key) for key in ('x', 'y', 'z')))
        self.assertEqual((1, 6), (scalar(root, 'pairx'), scalar(root, 'pairz')))
        self.assertEqual(3, root['pairx']['__type__'])
        self.assertEqual(inventory, root['Items'])
        self.assertEqual(5, render_actor(actor_data(cell))['facingDirection'])
        self.assertEqual(before, source.to_data())
        self.assertEqual(source.blocks, snapshot(result, ('rotate_y270',)).blocks)

    def test_closed_chest_door_bed_and_tallplant_parts_stay_paired(self):
        for identity in ('t04', 't03'):
            source = build(PREFIX + identity)
            source_pairs = 0
            for operation in OPERATIONS:
                result = snapshot(source, (operation,))
                self.assertEqual(len(source.blocks), len(result.blocks))
                for position, value in source.blocks.items():
                    target = transform_position(position, source.size, (operation,))
                    pair = actor_pair_position(value, position)
                    if pair is not None:
                        source_pairs += 1
                        expected = transform_position(pair, source.size, (operation,))
                        self.assertEqual(expected, actor_pair_position(result.get(target), target))
                    for index, layer_value in enumerate((foreground(value), background(value))):
                        relationship = group_partner(layer_value)
                        if relationship is None:
                            continue
                        source_pairs += 1
                        offset, unused = relationship
                        partner = tuple(position[axis] + offset[axis] for axis in range(3))
                        expected = transform_position(partner, source.size, (operation,))
                        transformed = group_partner(result.get_layer(target, index))
                        self.assertEqual(expected, tuple(target[axis] + transformed[0][axis]
                                                         for axis in range(3)))
                restored = snapshot(result, (INVERSES[operation],))
                self.assertEqual(source.size, restored.size)
                self.assertEqual(source.blocks, restored.blocks)
            self.assertGreater(source_pairs, 0)

    def test_isolated_halves_remain_isolated_without_inventing_partners(self):
        half = material('peony', {'upper_block_bit': True})
        source = Document((3, 5, 7), {(1, 4, 6): half})
        result = snapshot(source, ('mirror_y',))
        self.assertEqual(1, len(result.blocks))
        self.assertFalse(registry.states(result.get((1, 0, 6)))['upper_block_bit'])
        self.assertEqual(AIR, result.get((1, 1, 6)))

    def test_empty_document_and_maximum_non_square_dimensions(self):
        source = Document((64, 128, 1))
        result = snapshot(source, ('rotate_y90', 'mirror_y'))
        self.assertEqual((1, 128, 64), result.size)
        self.assertEqual(0, len(result.blocks))
        self.assertEqual([result.to_data()], [step.to_data() for step in iter_snapshot(
            source, ('rotate_y90', 'mirror_y'))])

    def test_invalid_operation_and_coordinate_fail_without_changing_source(self):
        source = non_symmetric()
        before = source.to_data()
        for operations in ('rotate_y90', None, ('rotate_y45',), ('move_xp',), (None,)):
            with self.subTest(operations=operations), self.assertRaises(ValueError):
                iter_snapshot(source, operations)
        for position in ((7, 0, 0), (0, -1, 0), (True, 0, 0), (0, 0)):
            with self.subTest(position=position), self.assertRaises(ValueError):
                transform_position(position, source.size)
        with self.assertRaises(ValueError):
            transform_size((65, 1, 1))
        self.assertEqual((), validate_operations())
        self.assertEqual(before, source.to_data())

    def test_unknown_native_state_aborts_without_publishing_partial_document(self):
        source = Document((3, 2, 4), {
            (0, 0, 0): material('stone'),
            (2, 1, 3): ('missing_namespace:unknown_direction', 0)})
        before = dict(source.blocks.items())
        steps = iter_snapshot(source, ('rotate_y90',))
        published = []
        with self.assertRaises(ValueError):
            for step in steps:
                if step is not None:
                    published.append(step)
        self.assertEqual([], published)
        self.assertEqual(before, dict(source.blocks.items()))
        self.assertEqual(source.blocks, snapshot(source).blocks)

    def test_repeated_complete_cells_preserve_both_layers_and_actor_origin_rules(self):
        front = material('oak_stairs', {'weirdo_direction': 0, 'upside_down_bit': False})
        back = material('dispenser', {'facing_direction': 5})
        repeated = make_cell(front, back)
        # Identical stored actor values may occur at different source positions.
        # Their root-coordinate deltas still depend on each cell's own origin.
        actor = make_cell(material('chest', {'minecraft:cardinal_direction': 'north'}),
                          nbt={'id': 'Chest', 'x': 1, 'y': 1, 'z': 1,
                               'pairx': 2, 'pairz': 1})
        source = Document((7, 5, 3), {
            (0, 0, 0): repeated, (6, 0, 2): repeated,
            (1, 1, 1): actor, (2, 1, 1): actor})
        result = snapshot(source, ('rotate_y90', 'mirror_y'))
        first, second = result.get((2, 4, 0)), result.get((0, 4, 6))
        self.assertEqual(first, second)
        self.assertEqual(2, registry.states(foreground(first))['weirdo_direction'])
        self.assertTrue(registry.states(foreground(first))['upside_down_bit'])
        self.assertEqual(3, registry.states(background(first))['facing_direction'])
        actors = [actor_data(result.get(position)) for position in ((1, 3, 1), (1, 3, 2))]
        self.assertEqual((1, 3, 1), tuple(actors[0][axis] for axis in ('x', 'y', 'z')))
        self.assertEqual((0, 3, 2), tuple(actors[1][axis] for axis in ('x', 'y', 'z')))
        self.assertEqual((1, 2), (actors[0]['pairx'], actors[0]['pairz']))
        self.assertEqual((1, 2), (actors[1]['pairx'], actors[1]['pairz']))


if __name__ == '__main__':
    unittest.main()
