"""Native block-state transforms use semantic fixtures and audit all records."""
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
        properties = {'direction': 0, 'head_piece_bit': True, 'occupied_bit': False}
        self.assertEqual(properties, transform.transform_states(properties, 'mirror_y'))

    def test_trapdoor_encoding_differs_from_bed_encoding(self):
        for name in registry.BLOCKS:
            if not name.endswith('_trapdoor') and name != 'minecraft:trapdoor':
                continue
            for aux in registry.aux_values(name):
                properties = registry.states((name, aux))
                quarter_turns = {0: 2, 1: 3, 2: 1, 3: 0}
                result = transform.transform_states(properties, 'rotate_y90')
                self.assertEqual(quarter_turns[properties['direction']], result['direction'])
                self.assertEqual(properties['open_bit'], result['open_bit'])
                self.assertEqual(properties['upside_down_bit'], result['upside_down_bit'])
                reflected = transform.transform_states(properties, 'mirror_y')
                self.assertEqual(not properties['upside_down_bit'], reflected['upside_down_bit'])
                self.assertEqual(properties['direction'], reflected['direction'])

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

    def test_vertical_mirror_keeps_upright_only_native_states(self):
        # Native state mirroring does not invent bottom torches or horizontal
        # crafters with a nonexistent *_down orientation.
        unchanged = (('minecraft:torch', 5), ('minecraft:crafter', 8),
                     ('minecraft:chest', 0), ('minecraft:furnace', 0),
                     ('minecraft:bell', 12), ('minecraft:lever', 1),
                     ('minecraft:brown_mushroom_block', 3),
                     ('minecraft:seagrass', 0), ('minecraft:bed', 4),
                     ('minecraft:acacia_standing_sign', 7))
        for value in unchanged:
            self.assertEqual(value, transform.transform(value, 'mirror_y'))
        self.assertEqual({'orientation': 'down_east'},
                         transform.transform_states({'orientation': 'up_east'}, 'mirror_y'))
        self.assertEqual({'attachment': 'hanging', 'direction': 1},
                         transform.transform_states({'attachment': 'standing', 'direction': 1}, 'mirror_y'))
        self.assertEqual({'lever_direction': 'down_east_west'},
                         transform.transform_states({'lever_direction': 'up_east_west'}, 'mirror_y'))

    def test_bookshelf_content_reflects_slots_without_inventing_orientation(self):
        source = {'books_stored': 1, 'direction': 0}
        self.assertEqual({'books_stored': 4, 'direction': 0},
                         transform.transform_states(source, 'mirror_x'))
        self.assertEqual({'books_stored': 8, 'direction': 0},
                         transform.transform_states(source, 'mirror_y'))
        self.assertEqual({'books_stored': 4, 'direction': 2},
                         transform.transform_states(source, 'mirror_z'))

    def test_mushroom_cap_faces_and_reserved_palette_codes(self):
        expected = {'rotate_y90': [3, 6, 9, 2, 5, 8, 1, 4, 7],
                    'mirror_x': [3, 2, 1, 6, 5, 4, 9, 8, 7],
                    'mirror_z': [7, 8, 9, 4, 5, 6, 1, 2, 3]}
        for operation, values in expected.items():
            for source, target in enumerate(values, 1):
                self.assertEqual({'huge_mushroom_bits': target},
                                 transform.transform_states({'huge_mushroom_bits': source}, operation))
        for operation in transform.OPERATIONS:
            for reserved in (11, 12, 13):
                value = ('minecraft:brown_mushroom_block', reserved)
                self.assertEqual(value, transform.transform(value, operation))

    def test_jigsaw_secondary_axis_respects_up_and_down_encodings(self):
        cases = (({'facing_direction': 0, 'rotation': 1}, 'rotate_y90',
                  {'facing_direction': 0, 'rotation': 0}),
                 ({'facing_direction': 1, 'rotation': 1}, 'rotate_y90',
                  {'facing_direction': 1, 'rotation': 2}),
                 ({'facing_direction': 0, 'rotation': 1}, 'mirror_y',
                  {'facing_direction': 1, 'rotation': 3}),
                 ({'facing_direction': 2, 'rotation': 3}, 'rotate_y90',
                  {'facing_direction': 5, 'rotation': 3}))
        for source, operation, target in cases:
            self.assertEqual(target, transform.transform_states(source, operation))

    def test_unreviewed_states_and_values_fail(self):
        with self.assertRaises(ValueError):
            transform.transform_states({'minecraft:future_direction': 'north'}, 'rotate_y90')
        with self.assertRaises(ValueError):
            transform.transform_states({'minecraft:cardinal_direction': 'north_up'}, 'rotate_y90')
        with self.assertRaises(ValueError):
            transform.transform_states({'huge_mushroom_bits': 16}, 'rotate_y90')
        with self.assertRaises(ValueError):
            transform.transform_states({'upside_down_bit': 1}, 'rotate_y90')

    def test_every_palette_state_has_a_native_target_and_restores_under_inverse(self):
        inverse = {'rotate_y90': 'rotate_y270', 'rotate_y180': 'rotate_y180',
                   'rotate_y270': 'rotate_y90', 'mirror_x': 'mirror_x',
                   'mirror_y': 'mirror_y', 'mirror_z': 'mirror_z'}
        count = 0
        for name in registry.BLOCKS:
            for aux in registry.aux_values(name):
                value = (name, aux)
                properties = registry.states(value)
                for operation in transform.OPERATIONS:
                    target = transform.transform(value, operation)
                    self.assertEqual(name, target[0])
                    self.assertIn(target[1], registry.aux_values(name))
                    restored = transform.transform(target, inverse[operation])
                    self.assertEqual(properties, registry.states(restored))
                count += 1
        self.assertEqual(registry.RECORD_COUNT, count)


if __name__ == '__main__':
    unittest.main()
