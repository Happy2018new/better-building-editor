"""NBT translations preserve typed wrappers, bytes and unrelated item data."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.nbt_spatial import rebase, root_payload, scalar


class NbtSpatialTests(unittest.TestCase):
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
