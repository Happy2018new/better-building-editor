"""Resource candidates must retain state coverage and native evidence boundaries."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from audit_render_compatibility import build, RESOURCES, report, SOURCE


class RenderCompatibilityInventoryTests(unittest.TestCase):
    def test_supplemental_education_animation_is_not_lost(self):
        palette = {'blocks': [{'name': 'minecraft:chemical_heat', 'data': n, 'states': []}
                              for n in range(2)]}
        resources = {RESOURCES[0]: {}, RESOURCES[1]: {'texture_data': {}}, RESOURCES[2]: []}
        extra = {'chemistry': {
            RESOURCES[0]: {'chemical_heat': {'textures': 'heat'}},
            RESOURCES[1]: {'texture_data': {}},
            RESOURCES[2]: [{'atlas_tile': 'heat', 'flipbook_texture': 'textures/heat'}]}}
        data = build(palette, {'game_version': 'old registry', 'source_sha256': 'AB'},
                     resources, {'block_entities': {}}, extra)
        self.assertEqual(['minecraft:chemical_heat'], data['ordinary_flipbook_names'])
        self.assertEqual(2, data['ordinary_flipbook_states'])
        self.assertEqual([], data['unmapped_after_supplemental_packs'])
        self.assertFalse(data['all_block_rows'][0]['pixel_qualified'])

    def test_nbt_texture_and_snapshot_pose_are_distinct_candidates(self):
        palette = {'blocks': [
            {'name': 'minecraft:campfire', 'data': 0, 'states': []},
            {'name': 'minecraft:door', 'data': 0, 'states': [{'name': 'open_bit'}]},
            {'name': 'minecraft:unknown', 'data': 0, 'states': []}]}
        resources = {RESOURCES[0]: {'campfire': {'textures': 'flame'}},
                     RESOURCES[1]: {'texture_data': {}},
                     RESOURCES[2]: [{'atlas_tile': 'flame', 'flipbook_texture': 'textures/flame'}]}
        defaults = {'block_entities': {'minecraft:campfire': {
            'nbt': {'id': {'__value__': 'Campfire'}}}}}
        data = build(palette, {'game_version': 'old registry', 'source_sha256': 'AB'}, resources, defaults)
        self.assertEqual([], data['ordinary_flipbook_names'])
        self.assertEqual(['minecraft:campfire'], data['nbt_flipbook_names'])
        door = next(row for row in data['all_block_rows'] if row['name'] == 'minecraft:door')
        self.assertEqual(['open_bit'], door['snapshot_pose_keys'])
        self.assertFalse(door['flipbook_candidate'])
        self.assertIn('minecraft:unknown', data['unmapped_after_supplemental_packs'])

    def test_checked_in_source_covers_every_retained_state_without_qualifying_pixels(self):
        data = report(SOURCE)
        self.assertEqual(15858, data['checked_states'])
        self.assertEqual(1340, data['checked_names'])
        self.assertEqual(15858, sum(len(row['aux_values']) for row in data['all_block_rows']))
        self.assertEqual(37, len(data['ordinary_flipbook_names']))
        self.assertEqual(12, len(data['nbt_flipbook_names']))
        self.assertEqual(24, len(data['unmapped_after_supplemental_packs']))
        self.assertFalse(data['particles_required'])
        self.assertTrue(all(not row['pixel_qualified'] for row in data['all_block_rows']))


if __name__ == '__main__':
    unittest.main()
