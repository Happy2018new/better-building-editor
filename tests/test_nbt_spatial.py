"""NBT translations preserve typed wrappers, bytes and unrelated item data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.nbt_spatial import rebase, root_payload, scalar, transform_pair


class NbtSpatialTests(unittest.TestCase):
    def test_untyped_value_metadata_does_not_replace_the_actor_root(self):
        data = {'id': 'Chest', 'x': 1, 'y': 3, 'z': 2, 'facingDirection': 2,
                '__value__': {'x': 900, 'pairx': 901, 'pairz': 902, 'facingDirection': 4}}
        self.assertIs(data, root_payload(data))
        moved = rebase(data, (3, -2, 5))
        self.assertEqual((4, 1, 7), tuple(scalar(moved, axis) for axis in ('x', 'y', 'z')))
        self.assertEqual(data['__value__'], moved['__value__'])
        self.assertEqual(data, rebase(moved, (-3, 2, -5)))
        rotated = transform_pair(data, (1, 3, 2), 'rotate_y90')
        self.assertEqual(5, rotated['facingDirection'])
        self.assertEqual(data['__value__'], rotated['__value__'])
        self.assertEqual(1, data['x'])
        self.assertEqual(900, data['__value__']['x'])

    def test_noncompound_type_metadata_is_not_unwrapped(self):
        for kind in (3, 9, 'TAG_List', b'TAG_List', 10.0, True, None):
            data = {'__type__': kind, '__value__': {'x': 900}, 'x': 1}
            self.assertIs(data, root_payload(data))
            moved = rebase(data, (3, 0, 0))
            self.assertEqual(4, moved['x'])
            self.assertEqual({'x': 900}, moved['__value__'])
            self.assertEqual(kind, moved['__type__'])

    def test_numeric_and_legacy_compound_markers_keep_byte_key_compatibility(self):
        for kind in (10, 'TAG_Compound', b'TAG_Compound'):
            for byte_keys in (False, True):
                type_key = b'__type__' if byte_keys else '__type__'
                value_key = b'__value__' if byte_keys else '__value__'
                x_key = b'x' if byte_keys else 'x'
                root = {x_key: {type_key: 3, value_key: 1}}
                data = {type_key: kind, value_key: root}
                self.assertIs(root, root_payload(data))
                moved = rebase(data, (3, 0, 0))
                self.assertEqual(4, scalar(root_payload(moved), 'x'))
                self.assertEqual(kind, moved[type_key])
                self.assertEqual(3, root_payload(moved)[x_key][type_key])
                self.assertEqual(data, rebase(moved, (-3, 0, 0)))

    def test_typed_root_and_pairs_round_trip_without_mutation(self):
        data = {'__type__': 10, '__value__': {
            'x': {'__type__': 3, '__value__': 103},
            'y': {'__type__': 3, '__value__': 64},
            'z': {'__type__': 3, '__value__': -2},
            'pairx': {'__type__': 3, '__value__': 104}, 'pairz': -2,
            'Items': [{'tag': {'x': 99, 'Command': 'tp @p 103 64 -2'}}]}}
        local = rebase(data, (-100, -64, 3))
        self.assertEqual(3, scalar(root_payload(local), 'x'))
        self.assertEqual(4, scalar(root_payload(local), 'pairx'))
        self.assertEqual(99, root_payload(local)['Items'][0]['tag']['x'])
        self.assertEqual(data, rebase(local, (100, 64, -3)))
        self.assertEqual(103, scalar(root_payload(data), 'x'))

    def test_sdk_byte_keys_remain_bytes_and_non_coordinates_unchanged(self):
        data = {b'x': {b'__type__': 3, b'__value__': 8}, b'y': 5,
                b'z': 10, b'Rotation': 2, b'custom': {b'x': 7}}
        result = rebase(data, (1, 2, 3))
        self.assertEqual({b'x', b'y', b'z', b'Rotation', b'custom'}, set(result))
        self.assertEqual(9, result[b'x'][b'__value__'])
        self.assertEqual(2, result[b'Rotation'])
        self.assertEqual({b'x': 7}, result[b'custom'])

    def test_absent_position_is_not_invented(self):
        self.assertEqual({'id': 'ShulkerBox'}, rebase({'id': 'ShulkerBox'}, (1, 2, 3)))
        self.assertIsNone(rebase(None, (1, 2, 3)))
