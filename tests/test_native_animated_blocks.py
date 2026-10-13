"""Resource audit must expand all states and expose unmatched animation sources."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_native_animated_blocks import inventory


class AnimatedBlockInventoryTests(unittest.TestCase):
    def test_nested_and_carried_tiles_expand_all_dumped_states(self):
        palette = {'blocks': [{'name': 'minecraft:fire', 'data': aux} for aux in range(4)]}
        blocks = {'fire': {'textures': {'up': 'flame'}, 'carried_textures': ['smoke']}}
        flips = [{'atlas_tile': name, 'flipbook_texture': 'textures/' + name} for name in ('flame', 'smoke')]
        data = inventory(palette, blocks, {}, flips)
        self.assertEqual(4, data['candidate_states'])
        self.assertEqual([0, 1, 2, 3], data['rows'][0]['aux_values'])
        self.assertEqual(['textures', 'carried_textures'], [r['usage'] for r in data['rows'][0]['associations']])
        self.assertFalse(data['rows'][0]['pixel_acceptance'])

    def test_flattened_tile_resolves_animation_by_identical_image(self):
        data = inventory({'blocks': [{'name': 'minecraft:sea_lantern', 'data': 0}]},
            {'seaLantern': {'textures': 'flattened_tile'}},
            {'texture_data': {'flattened_tile': {'textures': ['textures/blocks/sea_lantern.png']}}},
            [{'atlas_tile': 'sea_lantern', 'flipbook_texture': 'textures/blocks/sea_lantern'}])
        self.assertEqual(1, data['candidate_names'])
        self.assertEqual([], data['flipbook_entries_without_block_association'])

    def test_missing_definitions_and_unassociated_flipbooks_stay_unknown(self):
        data = inventory({'blocks': [{'name': 'minecraft:unmapped', 'data': 0}]},
            {'other': {'textures': 'animated'}}, {},
            [{'atlas_tile': name, 'flipbook_texture': 'textures/' + name} for name in ('animated', 'unknown')])
        self.assertEqual(0, data['candidate_names'])
        self.assertEqual(['minecraft:unmapped'], data['dump_names_without_direct_definition'])
        self.assertEqual(1, len(data['animated_definitions_missing_from_dump']))
        self.assertEqual([1], data['flipbook_entries_without_block_association'])

    def test_malformed_flipbook_is_rejected_instead_of_disappearing(self):
        with self.assertRaisesRegex(ValueError, 'explicit atlas tile'):
            inventory({'blocks': []}, {}, {}, [{'flipbook_texture': 'textures/fire'}])


if __name__ == '__main__':
    unittest.main()
