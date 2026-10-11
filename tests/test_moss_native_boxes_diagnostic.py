"""Reject false acceptance of native moss state and box evidence."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_moss_native_boxes as probe


class MossNativeBoxEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.pos = (12, 121, 8)
        self.expected = [{'pos': self.pos, 'value': ('minecraft:pale_moss_carpet', 8),
                          'states': {'pale_moss_carpet_side_east': 'short'}}]
        self.row = {'pos': list(self.pos), 'value': {'name': 'minecraft:pale_moss_carpet', 'aux': 8},
            'states': {'pale_moss_carpet_side_east': 'short'},
            'clip': {'min': [12, 121, 8], 'max': [13, 121.625, 9]},
            'collision': {'min': [12, 121, 8], 'max': [13, 121.0625, 9]},
            'collision_all': {'collision': []}}

    def test_native_pair_and_dict_match_without_equating_clip_and_collision(self):
        client = copy.deepcopy(self.row)
        client['value'] = ['minecraft:pale_moss_carpet', 8]
        result = probe.verify_snapshots({'server': {'rows': [self.row]},
                                         'client': {'rows': [client]}}, self.expected, [])
        self.assertTrue(result['original_values_exact'])
        self.assertTrue(result['native_boxes_stable_across_client_server_and_time'])

    def test_original_aux_states_and_unique_positions_are_required(self):
        changed_aux = copy.deepcopy(self.row)
        changed_aux['value']['aux'] = 0
        changed_states = copy.deepcopy(self.row)
        changed_states['states']['pale_moss_carpet_side_east'] = 'none'
        for rows in ([changed_aux], [changed_states], [], [self.row, self.row]):
            with self.subTest(rows=rows), self.assertRaises(AssertionError):
                probe.verify_snapshots({'native': {'rows': rows}}, self.expected, [])

    def test_later_box_drift_is_rejected_even_with_unchanged_states(self):
        later = copy.deepcopy(self.row)
        later['clip']['max'][1] = 121.5
        with self.assertRaises(AssertionError):
            probe.verify_snapshots({'first': {'rows': [self.row]},
                                    'later': {'rows': [later]}}, self.expected, [])

    def test_zero_collision_and_empty_native_envelope_are_valid_raw_structures(self):
        zero = {'min': [0, 0, 0], 'max': [0, 0, 0]}
        self.assertTrue(probe.box_structure(zero)['zero_extent'])
        self.assertEqual(probe.box_structure({'collision': []}),
                         {'kind': 'collision_envelope', 'boxes': []})
        for invalid in ({'collision': None}, {'min': [0, 0, 0]},
                        {'min': [1, 0, 0], 'max': [0, 0, 0]},
                        {'min': [0, 0, 0], 'max': [float('nan'), 1, 1]}):
            with self.subTest(invalid=invalid), self.assertRaises(AssertionError):
                probe.box_structure(invalid)

    def test_stone_positive_control_requires_default_unit_boxes(self):
        row = copy.deepcopy(self.row)
        row.update(value=['minecraft:stone', 0], states={})
        row['clip'] = row['collision'] = {'min': [12, 121, 8], 'max': [13, 122, 9]}
        self.assertTrue(probe.verify_snapshots({'native': {'rows': [row]}}, [],
                         [(self.pos, ('minecraft:stone', 0))])['stone_default_unit_boxes'])
        row['clip']['max'][1] = 121.0625
        with self.assertRaises(AssertionError):
            probe.verify_snapshots({'native': {'rows': [row]}}, [],
                                   [(self.pos, ('minecraft:stone', 0))])

    def test_air_replication_rejects_duplicate_coordinates_and_unloaded_values(self):
        expected = {(0, 1, 0): ('minecraft:air', 0), (1, 1, 0): ('minecraft:air', 0)}
        first = {'pos': [0, 1, 0], 'value': ['minecraft:air', 0]}
        second = {'pos': [1, 1, 0], 'value': ['minecraft:air', 0]}
        self.assertTrue(probe.replicated({'rows': [first, second]}, expected))
        self.assertFalse(probe.replicated({'rows': [first, first]}, expected))
        second['value'] = None
        self.assertFalse(probe.replicated({'rows': [first, second]}, expected))


if __name__ == '__main__':
    unittest.main()
