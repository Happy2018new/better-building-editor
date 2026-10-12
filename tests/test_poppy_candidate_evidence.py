"""Finite poppy evidence cannot silently promote runtime defaults or hide failures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import build_poppy_candidate_evidence_r10b as evidence


class PoppyCandidateEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT/'tools/data/snow-poppy-candidate-all-height-evidence-r10b.json').read_bytes())

    def report(self):
        rows = [deepcopy(next(row for row in self.manifest['rows']
                             if row['view'] == 'public' and row['height'] == 0 and row['kind'] == kind))
                for kind in ('plant', 'snow', 'covered')]
        for row in rows:
            row['comparisons'] = row.pop('world')
        return {'plants': ['poppy'], 'view': 'public', 'heights': [0],
                'limits': deepcopy(evidence.LIMITS), 'world_camera_offset': evidence.VIEWS['public'],
                'native_target': evidence.TARGET, 'modes': ['full', 'missing'],
                'completed': True, 'restored': True, 'passed': True,
                'source_assets_stable': True, 'native_resolution': True, 'near_player': True,
                'cleanup_errors': [], 'binding_read_failures': [],
                'native_cleanup': [{'clean': True}], 'rows': rows}

    def test_candidate_scope_and_default_nonregistration_are_preserved(self):
        manifest = self.manifest
        self.assertFalse(manifest['production_acceptance'])
        self.assertFalse(manifest['production_default_enabled'])
        self.assertFalse(manifest['runtime_position_scope_enforced'])
        scope = manifest['measured_scope']
        self.assertEqual(evidence.TARGET, scope['native_target'])
        self.assertEqual(evidence.VIEWS, scope['views'])
        self.assertFalse(scope['other_positions_or_runtime_versions_accepted'])
        self.assertFalse(scope['native_mesh_authority'])
        self.assertFalse(scope['random_offset_contract_recovered'])
        namespace = {}
        exec((ROOT/'behavior_pack/modern_projection/projection/plant_proxy_data.py').read_text(encoding='utf8'), namespace)
        expected = {('minecraft:'+name, 0) for name in
                    ('brown_mushroom', 'red_mushroom', 'crimson_fungus', 'warped_fungus')}
        self.assertEqual(expected, set(namespace['STATIC_PLANT_PROXIES']))
        self.assertEqual(expected, set(namespace['STATIC_PLANT_ACCEPTANCE']))
        blocks = json.loads((ROOT/'resource_pack/blocks.json').read_bytes())
        atlas = json.loads((ROOT/'resource_pack/textures/terrain_texture.json').read_bytes())
        self.assertNotIn('modern_projection:preview_poppy', blocks)
        self.assertNotIn('modern_projection_static_poppy', atlas['texture_data'])
        for relative in evidence.ASSETS:
            self.assertFalse((ROOT/relative).exists())

    def test_isolated_resource_bytes_match_both_measured_height_partitions(self):
        for relative, expected in evidence.ASSETS.items():
            artifact = self.manifest['candidate_assets'][relative]
            path = ROOT/artifact['isolated_resource']
            self.assertTrue(path.is_relative_to(ROOT/'tools/data'))
            self.assertEqual(expected, artifact['sha256'])
            self.assertEqual(expected, hashlib.sha256(path.read_bytes()).hexdigest())
        registration = json.loads((ROOT/evidence.RESOURCE_DIR/'registration.json').read_bytes())
        self.assertFalse(registration['production_default_enabled'])
        self.assertFalse(registration['runtime_position_scope_enforced'])
        self.assertEqual({'textures': 'textures/blocks/flower_rose'}, registration['texture_entry'])

    def test_disjoint_union_keeps_failed_mixed_family_verdicts(self):
        partitions = self.manifest['evidence_partitions']
        first, rest = partitions['h0'], partitions['h1_h7']
        self.assertFalse(first['original_matrix_passed'])
        self.assertTrue(rest['original_matrix_passed'])
        self.assertFalse(set(first['snow_heights']) & set(rest['snow_heights']))
        self.assertEqual(set(range(8)), set(first['snow_heights']) | set(rest['snow_heights']))
        self.assertEqual(138, first['failed_rows'][0]['native_roi_boundary']['clipped_boundary_pixels'])
        self.assertFalse(self.manifest['preserved_failed_screen']['original_matrix_passed'])
        covered = [row for row in self.manifest['rows'] if row['kind'] == 'covered']
        self.assertEqual(16, len(covered))
        self.assertEqual({(view, height) for view in evidence.VIEWS for height in range(8)},
                         {(row['view'], row['height']) for row in covered})
        for row in covered:
            self.assertTrue(row['editor_controls']['passed'])
            for comparison in row['world'].values():
                plant = comparison['masks']['exposed_plant']
                self.assertTrue(plant['passed'])
                if row['height'] >= 5:
                    self.assertEqual((0, 0), (plant['expected_pixels'], plant['observed_pixels']))
                    self.assertEqual(0, row['editor_controls']['covered_contribution_pixels'])
                else:
                    self.assertGreaterEqual(plant['recall'], .75)
                    self.assertGreaterEqual(plant['precision'], .75)

    def test_combined_snow_success_cannot_hide_failed_or_missing_exposed_plant(self):
        evidence.validate_report(self.report(), 'public', [0])
        for failure in ('failed', 'missing'):
            report = self.report()
            covered = next(row for row in report['rows'] if row['kind'] == 'covered')
            masks = covered['comparisons']['full']['masks']
            if failure == 'failed':
                masks['exposed_plant']['passed'] = False
            else:
                del masks['exposed_plant']
            with self.subTest(failure=failure), self.assertRaisesRegex(ValueError, 'mask'):
                evidence.validate_report(report, 'public', [0])

    def test_scope_roi_and_capture_backend_cannot_be_relaxed(self):
        for failure in ('cell', 'height', 'threshold', 'roi', 'legacy'):
            report = self.report()
            if failure == 'cell':
                report['native_target'] = [0, 117, 0]
            elif failure == 'height':
                report['heights'] = [0, 1]
            elif failure == 'threshold':
                report['limits']['native_recall'] = .7
            elif failure == 'roi':
                report['rows'][0]['world_roi']['method'] = 'expanded visual fit'
            else:
                report['extra_capture'] = {'path': 'original.png', 'sha256': '0'*64,
                                           'capture': {'backend': 'PrintWindow', 'reliable': True}}
            with self.subTest(failure=failure), self.assertRaises(ValueError):
                evidence.validate_report(report, 'public', [0])

    def test_changed_original_report_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'report.json'
            path.write_bytes(b'{"passed": true}')
            reference = evidence.record(path)
            path.write_bytes(b'{"passed": false}')
            with self.assertRaisesRegex(ValueError, 'Original evidence changed'):
                evidence.checked(reference)


if __name__ == '__main__':
    unittest.main()
