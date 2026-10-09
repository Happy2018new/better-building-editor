"""Native block-state transforms use semantic fixtures and audit all records."""
import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection import state_transform as transform


class StateTransformTests(unittest.TestCase):
    def test_stair_direction_and_half_fixtures(self):
        expected = {
            'rotate_y90': ([2, 3, 1, 0], False),
            'rotate_y180': ([1, 0, 3, 2], False),
            'rotate_y270': ([3, 2, 0, 1], False),
            'mirror_x': ([1, 0, 2, 3], False),
            'mirror_y': ([0, 1, 2, 3], True),
            'mirror_z': ([0, 1, 3, 2], False),
        }
        for operation, (directions, upside_down) in expected.items():
            for direction in range(4):
                for source_half in (False, True):
                    result = transform.transform_states(
                        {'weirdo_direction': direction, 'upside_down_bit': source_half}, operation)
                    self.assertEqual(directions[direction], result['weirdo_direction'])
                    target_half = not source_half if operation == 'mirror_y' else source_half
                    self.assertEqual(target_half, result['upside_down_bit'])

    def test_rail_shapes_use_geometric_fixtures(self):
        expected = {
            'rotate_y90': [1, 0, 5, 4, 2, 3, 7, 8, 9, 6],
            'rotate_y180': [0, 1, 3, 2, 5, 4, 8, 9, 6, 7],
            'rotate_y270': [1, 0, 4, 5, 3, 2, 9, 6, 7, 8],
            'mirror_x': [0, 1, 3, 2, 4, 5, 7, 6, 9, 8],
            'mirror_y': [0, 1, 3, 2, 5, 4, 6, 7, 8, 9],
            'mirror_z': [0, 1, 2, 3, 5, 4, 9, 8, 7, 6],
        }
        for operation, values in expected.items():
            for value, result_value in enumerate(values):
                self.assertEqual({'rail_direction': result_value},
                    transform.transform_states({'rail_direction': value}, operation))

    def test_bed_directions_and_multiblock_state_bits(self):
        expected = {
            'rotate_y90': [1, 2, 3, 0],
            'rotate_y180': [2, 3, 0, 1],
            'rotate_y270': [3, 0, 1, 2],
            'mirror_x': [0, 3, 2, 1],
            'mirror_z': [2, 1, 0, 3],
        }
        for operation, directions in expected.items():
            for direction in range(4):
                properties = {'direction': direction, 'head_piece_bit': True,
                              'occupied_bit': False}
                result = transform.transform_states(properties, operation)
                self.assertEqual(directions[direction], result['direction'])
                self.assertTrue(result['head_piece_bit'])
                self.assertFalse(result['occupied_bit'])
        with self.assertRaises(transform.UnrepresentableTransform):
            transform.transform_states({'direction': 0, 'head_piece_bit': True,
                                        'occupied_bit': False}, 'mirror_y')

    def test_doors_tall_plants_and_vertical_halves(self):
        door = registry.states(('minecraft:acacia_door', 0))
        top = dict(door, upper_block_bit=True)
        for operation in transform.OPERATIONS:
            lower_result = transform.transform_states(door, operation)
            upper_result = transform.transform_states(top, operation)
            self.assertEqual(not lower_result['upper_block_bit'], upper_result['upper_block_bit'])
            for key in door:
                if key != 'upper_block_bit':
                    self.assertEqual(lower_result[key], upper_result[key])
        self.assertTrue(transform.transform_states(door, 'mirror_x')['door_hinge_bit'])
        self.assertTrue(transform.transform_states(door, 'mirror_z')['door_hinge_bit'])
        self.assertFalse(transform.transform_states(door, 'rotate_y90')['door_hinge_bit'])
        self.assertTrue(transform.transform_states(door, 'mirror_y')['upper_block_bit'])

        tall_plant = registry.states(('minecraft:sunflower', 0))
        self.assertFalse(tall_plant['upper_block_bit'])
        self.assertTrue(transform.transform_states(tall_plant, 'mirror_y')['upper_block_bit'])
        self.assertEqual(tall_plant,
            transform.transform_states(tall_plant, 'rotate_y90'))

    def test_connection_properties_move_without_stale_keys(self):
        source = {'wall_connection_type_east': 'short',
                  'wall_connection_type_north': 'tall'}
        self.assertEqual({'wall_connection_type_south': 'short',
                          'wall_connection_type_east': 'tall'},
                         transform.transform_states(source, 'rotate_y90'))

    def test_unrepresentable_and_unreviewed_states_fail(self):
        with self.assertRaises(transform.UnrepresentableTransform):
            transform.transform(('minecraft:torch', 5), 'mirror_y')
        with self.assertRaises(transform.UnrepresentableTransform):
            transform.transform(('minecraft:crafter', 8), 'mirror_y')
        with self.assertRaises(transform.UnrepresentableTransform):
            transform.transform(('minecraft:chiseled_bookshelf', 0), 'mirror_y')
        with self.assertRaises(transform.UnrepresentableTransform):
            transform.transform(('minecraft:brown_mushroom_block', 11), 'rotate_y90')
        with self.assertRaises(ValueError):
            transform.transform_states({'minecraft:future_direction': 'north'}, 'rotate_y90')
        with self.assertRaises(ValueError):
            transform.transform_states({'minecraft:cardinal_direction': 'north_up'}, 'rotate_y90')

    def test_all_palette_states_transform_or_fail_explicitly(self):
        resolved = collections.Counter()
        unavailable = collections.Counter()
        for name in registry.BLOCKS:
            for aux in registry.aux_values(name):
                value = (name, aux)
                properties = registry.states(value)
                for operation in transform.OPERATIONS:
                    try:
                        target_properties = transform.transform_states(properties, operation)
                    except transform.UnrepresentableTransform:
                        with self.assertRaises(transform.UnrepresentableTransform):
                            transform.transform(value, operation)
                        unavailable[operation] += 1
                        continue
                    target = registry.from_states(name, target_properties)
                    if target is None:
                        with self.assertRaises(transform.UnrepresentableTransform):
                            transform.transform(value, operation)
                        unavailable[operation] += 1
                    else:
                        self.assertEqual(target, transform.transform(value, operation))
                        self.assertEqual(target_properties, registry.states(target))
                        resolved[operation] += 1
        self.assertEqual(set(transform.OPERATIONS), set(resolved) | set(unavailable))
        self.assertTrue(all(resolved[operation] for operation in transform.OPERATIONS))


if __name__ == '__main__':
    unittest.main()
