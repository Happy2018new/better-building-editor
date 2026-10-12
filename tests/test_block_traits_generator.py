import copy
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('generate_block_traits', ROOT / 'tools/generate_block_traits.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class WaterTraitGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.data = {'game_version': 'Native test version', 'palette_sha256': 'abc'}
        self.palette = {'blocks': [
            {'name': 'minecraft:full', 'data': 0}, {'name': 'minecraft:full', 'data': 1},
            {'name': 'minecraft:partial', 'data': 0}, {'name': 'minecraft:partial', 'data': 3},
            {'name': 'minecraft:none', 'data': 0}, {'name': 'custom:ignored', 'data': 0}]}
        self.water = {'schema': 1, 'game_version': self.data['game_version'],
                      'palette_sha256': 'ABC', 'method': generator.WATER_PROBE_METHOD,
                      'tested_states': 5, 'total_states': 5, 'verified_states': 5,
                      'blocks': {'minecraft:full': True, 'minecraft:partial': [3],
                                 'minecraft:none': False}}

    def test_measured_all_states_and_partial_aux_sets_are_kept_separate(self):
        names, partial = generator._water_rows(self.water, self.data, self.palette)
        self.assertEqual(['minecraft:full'], names)
        self.assertEqual({'minecraft:partial': [3]}, partial)
        self.assertEqual([3], self.water['blocks']['minecraft:partial'])

    def test_all_accepted_aux_list_is_compacted_to_a_whole_native_name(self):
        self.water['blocks']['minecraft:partial'] = [3, 0]
        names, partial = generator._water_rows(self.water, self.data, self.palette)
        self.assertEqual(['minecraft:full', 'minecraft:partial'], names)
        self.assertEqual({}, partial)

    def test_unfinished_wrong_version_and_unproven_old_exports_are_rejected(self):
        for field, value in (('tested_states', 4), ('total_states', 6),
                             ('verified_states', 4),
                             ('game_version', 'Other version'), ('method', 'CanBlockBePlacedLiquid'),
                             ('palette_sha256', 'wrong'), ('schema', 2)):
            water = dict(self.water, **{field: value})
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    generator._water_rows(water, self.data, self.palette)
        water = copy.deepcopy(self.water)
        water['blocks'].pop('minecraft:none')
        with self.assertRaises(ValueError):
            generator._water_rows(water, self.data, self.palette)

    def test_invalid_aux_and_boolean_aux_are_rejected(self):
        for accepted in ([True], [4], [3, 3], 1, {'3': True}):
            water = copy.deepcopy(self.water)
            water['blocks']['minecraft:partial'] = accepted
            with self.subTest(accepted=accepted):
                with self.assertRaises(ValueError):
                    generator._water_rows(water, self.data, self.palette)


class SnowEvidenceGeneratorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((ROOT / 'tools/data/native_block_metadata_nemc_3.9.0.401155.json').read_text(encoding='utf8'))
        cls.palette = json.loads((ROOT / 'docs/reference/block_palettes/nemc_3.9.0.401155.json').read_text(encoding='utf8'))
        cls.observations = json.loads((ROOT / 'tools/data/native_snow_states_nemc_3.9.0.401155.json').read_text(encoding='utf8'))
        cls.paired = json.loads((ROOT / 'tools/data/native_paired_snow_nemc_3.9.0.401155.json').read_text(encoding='utf8'))

    def test_exact_positive_and_paired_lower_states_are_kept_without_seed_extrapolation(self):
        supported, unsupported = generator._snow_evidence_rows(self.observations, self.paired, self.data, self.palette)
        self.assertEqual((29, 8), (len(supported), len(unsupported)))
        self.assertEqual([0], supported['minecraft:poppy'])
        self.assertEqual([0], unsupported['minecraft:tall_grass'])
        self.assertEqual([14], unsupported['minecraft:pitcher_crop'])
        self.assertNotIn('minecraft:acacia_door', unsupported)

    def test_mismatched_source_schema_version_palette_or_method_is_rejected(self):
        for source_name in ('observations', 'paired'):
            for field, value in (('schema', 99), ('game_version', 'NEMC future'),
                                 ('palette_sha256', '0' * 64), ('method', 'seed API return only')):
                sources = {'observations': self.observations, 'paired': self.paired}
                sources[source_name] = dict(sources[source_name], **{field: value})
                with self.subTest(source=source_name, field=field), self.assertRaises(ValueError):
                    generator._snow_evidence_rows(sources['observations'], sources['paired'], self.data, self.palette)

    def test_incomplete_or_changed_positive_readbacks_are_rejected(self):
        for failure in ('unfinished', 'unrestored', 'missing_height', 'duplicate', 'unknown_aux', 'delayed'):
            source = copy.deepcopy(self.observations)
            if failure == 'unfinished': source['done'] = False
            elif failure == 'unrestored': source['restored'] = False
            elif failure == 'missing_height': source['rows'].pop()
            elif failure == 'duplicate': source['rows'].append(copy.deepcopy(source['rows'][0]))
            elif failure == 'unknown_aux': source['rows'][0]['aux'] = 999
            else: source['rows'][0]['delayed']['back'][0] = 'minecraft:air'
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                generator._snow_evidence_rows(source, self.paired, self.data, self.palette)

    def test_negative_requires_a_verified_complete_pair_and_unchanged_readback(self):
        for failure in ('unverified', 'wrong_aux', 'missing_pair', 'upper_state', 'upper_position', 'changed', 'duplicate'):
            source = copy.deepcopy(self.paired)
            row = next(row for row in source['rows'] if row['name'] == 'minecraft:tall_grass')
            if failure == 'unverified': row['dry_verified'] = False
            elif failure == 'wrong_aux': row['aux'] = 1
            elif failure == 'missing_pair': row['paired'] = False
            elif failure == 'upper_state': row['dry'][1]['states']['upper_block_bit'] = False
            elif failure == 'upper_position': row['dry'][1]['pos'][1] += 1
            elif failure == 'changed': row['snowy'][0]['front']['name'] = 'minecraft:snow_layer'
            else: source['rows'].append(copy.deepcopy(row))
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                generator._snow_evidence_rows(self.observations, source, self.data, self.palette)

    def test_different_valid_growth_state_does_not_complete_the_measured_pair(self):
        source = copy.deepcopy(self.paired)
        row = next(row for row in source['rows'] if row['name'] == 'minecraft:pitcher_crop')
        row['dry'][1]['front']['aux'] = 13
        row['dry'][1]['states']['growth'] = 6
        row['dry'][1]['layers']['common'][0][1] = 13
        row['snowy'] = copy.deepcopy(row['dry'])
        with self.assertRaisesRegex(ValueError, 'complete lower/upper pair'):
            generator._snow_evidence_rows(self.observations, source, self.data, self.palette)


if __name__ == '__main__':
    unittest.main()
