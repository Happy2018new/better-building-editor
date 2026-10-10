import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from diff_block_entities import compare, nbt_identifier


class BlockEntityReferenceTests(unittest.TestCase):
    def setUp(self):
        self.reference = {'schema_version': 1, 'entities': [
            {'id': 2, 'name': 'Chest'}, {'id': 25, 'name': 'ShulkerBox'}]}

    def test_reference_preserves_all_user_records_and_remains_unconfirmed(self):
        reference = json.loads((ROOT / 'docs/reference/block_entities/nemc_3.9_reference.json').read_text())
        self.assertEqual(59, len(reference['entities']))
        self.assertFalse(reference['version']['native_verified'])
        by_id = {row['id']: row['name'] for row in reference['entities']}
        self.assertEqual('CopperGolemStatue', by_id[60])
        self.assertEqual('ModBlock', by_id[255])
        self.assertNotIn(20, by_id)

    def test_native_cells_read_tagged_nbt_ids_without_inferring_numeric_ids(self):
        probe = {'schema': 1, 'actors': [
            {'name': 'chest', 'cells': [
                {'pos': [1, 2, 3], 'front': {'name': 'minecraft:chest', 'aux': 2},
                 'nbt': {'id': {'__type__': 8, '__value__': 'Chest'}, 'Items': []}},
                {'nbt': {'__type__': 10, '__value__': {
                    'id': {'__type__': 8, '__value__': 'Chest'}}}},
                {'nbt': None}]}]}
        report = compare(self.reference, probe)
        match = report['matched_names'][0]
        self.assertEqual('Chest', match['name'])
        self.assertEqual(2, match['observed_count'])
        self.assertEqual([], match['observed_enum_ids'])
        self.assertFalse(match['numeric_id_verified_by_input'])
        self.assertEqual(['ShulkerBox'], report['reference_names_unobserved_in_sample'])

    def test_empty_payloads_and_block_case_names_do_not_invent_entities(self):
        report = compare(self.reference, {'actors': [
            {'name': 'Chest', 'cells': [{'front': {'name': 'minecraft:chest'}, 'nbt': {}},
                                       {'nbt': {'custom': {'id': 'Chest'}}}]}]})
        self.assertEqual(0, report['observed_entity_name_count'])
        self.assertIsNone(nbt_identifier({'id': 2}))

    def test_explicit_numeric_enum_ids_report_conflicts_and_unknown_names(self):
        report = compare(self.reference, {'schema_version': 1, 'entities': [
            {'name': 'Chest', 'enum_id': 2}, {'name': 'ShulkerBox', 'id': 26},
            {'name': 'NewEntity', 'enum_id': 300}]})
        self.assertTrue(report['matched_names'][0]['numeric_id_verified_by_input'])
        self.assertEqual('ShulkerBox', report['numeric_id_conflicts'][0]['name'])
        self.assertEqual('NewEntity', report['unknown_observed_names'][0]['name'])

    def test_reference_and_observation_validation_reject_ambiguous_ids(self):
        for entities in ([{'id': 2, 'name': 'Chest'}, {'id': 2, 'name': 'Other'}],
                         [{'id': 2, 'name': 'Chest'}, {'id': 3, 'name': 'Chest'}]):
            with self.assertRaises(ValueError):
                compare({'schema_version': 1, 'entities': entities}, {'entities': []})
        for data in ({'entities': [{'name': 'Chest', 'id': True}]},
                     {'actors': {}}, {'blocks': [{'name': 'minecraft:chest'}]}):
            with self.assertRaises(ValueError):
                compare(self.reference, data)


if __name__ == '__main__':
    unittest.main()
