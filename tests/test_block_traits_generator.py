import copy
import importlib.util
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


if __name__ == '__main__':
    unittest.main()
