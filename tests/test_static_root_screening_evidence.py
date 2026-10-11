"""Rejected root silhouettes cannot be promoted by editor or snow-only controls."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))


class StaticRootScreeningEvidenceTests(unittest.TestCase):
    def test_original_omissions_and_centered_cross_failures_remain_distinct(self):
        evidence = json.loads((ROOT/'tools/data/snow-static-roots-rejected-screening-r8.json').read_bytes())
        self.assertFalse(evidence['production_acceptance'])
        self.assertFalse(evidence['all_eight_snow_heights_accepted'])
        self.assertFalse(evidence['remaining_height_matrix_started'])
        self.assertEqual({'native_recall': .75, 'native_precision': .75,
                          'native_edge_tolerance_pixels': 3}, evidence['original_gates'])
        raw, candidate = evidence['raw_omissions'], evidence['centered_cross_hypothesis']
        self.assertEqual(3, len(raw['reports']))
        self.assertEqual(6, len(candidate['reports']))
        self.assertEqual(72, raw['unique_native_pngs'])
        self.assertEqual(138, candidate['unique_native_pngs'])
        for partition in (raw, candidate):
            self.assertTrue(partition['completed'])
            self.assertTrue(partition['restored'])
            self.assertFalse(partition['passed'])
            self.assertTrue(partition['foreground_changes_are_diagnostics'])
            self.assertTrue(all(not row['passed'] for row in partition['reports']))
            for row in partition['rows']:
                if row['kind'] == 'covered':
                    for mode in ('full', 'missing'):
                        self.assertFalse(row['world'][mode]['masks']['exposed_plant']['passed'])
        self.assertTrue(all(row['editor_controls']['passed'] for row in candidate['rows']
                            if row['kind'] == 'covered'))
        for row in raw['rows']:
            if row['kind'] == 'plant':
                self.assertEqual(0, row['world']['full']['masks']['object']['observed_pixels'])

    def test_failed_candidates_are_absent_from_production_registration(self):
        from projection.plant_proxy_data import STATIC_PLANT_PROXIES
        evidence = json.loads((ROOT/'tools/data/snow-static-roots-rejected-screening-r8.json').read_bytes())
        blocks = json.loads((ROOT/'resource_pack/blocks.json').read_bytes())
        atlas = json.loads((ROOT/'resource_pack/textures/terrain_texture.json').read_bytes())['texture_data']
        for name in evidence['plants']:
            self.assertNotIn(('minecraft:'+name, 0), STATIC_PLANT_PROXIES)
            self.assertNotIn('modern_projection:preview_'+name, blocks)
            self.assertNotIn('modern_projection_static_'+name, atlas)
            self.assertFalse((ROOT/'behavior_pack/netease_blocks'/('preview_'+name+'.json')).exists())
            self.assertFalse((ROOT/'resource_pack/models/netease_block'/('preview_'+name+'.json')).exists())


if __name__ == '__main__':
    unittest.main()
