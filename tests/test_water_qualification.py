"""Reject incomplete occupancy and stale capture bundles before water admission."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
spec = importlib.util.spec_from_file_location('water_qualification', ROOT / 'tools/qualify_water_product_r16.py')
qualification = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qualification)


def state(positions, keep=3):
    records = []
    for position in positions:
        origin = tuple(axis // 4 * 4 for axis in position)
        local = tuple(position[axis] - origin[axis] for axis in range(3))
        address = local[0] + local[2] * 4 + local[1] * 16
        records.append({'visible': True, 'group': ['key', 'model', origin,
            [[address | (63 << 6), 0, 0, 0], [0] * 4, [0] * 4, [39686, -1, 0, 1]]]})
    return {'liquid_groups': records, 'occupancy': {'rendered_keep': keep},
            'source_cells': [['saved-pool-data']]}


class WaterQualificationTests(unittest.TestCase):
    def test_frozen_case_batches_need_exact_complete_nonduplicate_coverage(self):
        cases = [row['id'] for row in qualification.CASES]
        reports = []
        for route in qualification.ROUTES:
            for subset in (cases[:6], cases[6:12], cases[12:]):
                reports.append({'frozen': True, 'routes': [route], 'cases': subset,
                    'rows': {route + '_' + case + '_' + control: {}
                             for case in subset for control in ('wet', 'dry')}})
        expected = {(route, case) for route in qualification.ROUTES for case in cases}
        self.assertEqual(expected, qualification.frozen_coverage(reports))
        with self.assertRaisesRegex(ValueError, 'lacks public cases/routes'):
            qualification.frozen_coverage(reports[:-1])
        with self.assertRaisesRegex(ValueError, 'duplicate display-route cases'):
            qualification.frozen_coverage(reports + [reports[0]])
        incomplete = copy.deepcopy(reports)
        del incomplete[0]['rows'][next(iter(incomplete[0]['rows']))]
        with self.assertRaisesRegex(ValueError, 'lacks paired public controls'):
            qualification.frozen_coverage(incomplete)

    def report(self):
        positions = {(3, 3, 3), (4, 3, 3), (3, 3, 4), (4, 3, 4)}
        original = state(positions)
        return {'rows': {'missing_pool_wet': {'ready': original}}, 'extra_rows': {
            'missing_pool_wet_occupied': state(positions - {(3, 3, 3)}, 2),
            'missing_pool_wet_restored': state(positions)}}

    def test_exact_occupied_cell_must_disappear_and_all_four_must_restore(self):
        report = self.report()
        qualification.occupancy(report)
        occupied = report['extra_rows']['missing_pool_wet_occupied']
        occupied['liquid_groups'].extend(report['rows']['missing_pool_wet']['ready']['liquid_groups'])
        with self.assertRaisesRegex(ValueError, 'exactly one published cell'):
            qualification.occupancy(report)

    def test_wrong_occupied_cell_and_missing_restore_reject(self):
        positions = {(3, 3, 3), (4, 3, 3), (3, 3, 4), (4, 3, 4)}
        for field, value in (
            ('missing_pool_wet_occupied', state(positions - {(4, 3, 3)}, 2)),
            ('missing_pool_wet_restored', state(positions - {(3, 3, 3)}))):
            with self.subTest(field=field):
                report = self.report()
                report['extra_rows'][field] = value
                with self.assertRaisesRegex(ValueError, 'exactly one published cell'):
                    qualification.occupancy(report)

    def test_source_change_rejects_even_when_displayed_cells_restore(self):
        report = self.report()
        report['extra_rows']['missing_pool_wet_occupied']['source_cells'] = [['modified-pool']]
        with self.assertRaisesRegex(ValueError, 'preserve and restore its source'):
            qualification.occupancy(report)

    def test_zero_slots_hidden_models_and_duplicate_faces_do_not_add_cells(self):
        original = state({(4, 3, 4)})
        duplicate = copy.deepcopy(original['liquid_groups'][0])
        duplicate['group'][3][0][0] |= 200 << 12
        original['liquid_groups'].append(duplicate)
        hidden = state({(3, 3, 3)})['liquid_groups'][0]
        hidden['visible'] = False
        original['liquid_groups'].append(hidden)
        self.assertEqual({(4, 3, 4)}, qualification.published_positions(original))

    def test_captured_shader_and_shared_registration_changes_reject(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            source = 'owner.py'
            data = qualification.MODULE + 'liquid_product_resource_data.py'
            shader = 'resource_pack/shader.fragment'
            registration = 'resource_pack/models/netease_models.json'
            for name in (source, data, shader, registration):
                path = project / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'captured')
            report = {'source_file_sha256_before': {
                name: qualification.sha(project / name) for name in (source, data, shader, registration)}}
            contract = {'output_sha256': {name: qualification.sha(project / name)
                                         for name in (shader, registration)}}
            with patch.object(qualification, 'SOURCES', (source,)):
                qualification.source_closure(project, report, contract)
                for name in (source, shader, registration):
                    with self.subTest(name=name):
                        path = project / name
                        path.write_bytes(b'changed')
                        with self.assertRaises(ValueError):
                            qualification.source_closure(project, report, contract)
                        path.write_bytes(b'captured')

    def test_separate_completed_routes_combine_without_reusing_failed_evidence(self):
        editor = {'evidence_valid': True, 'visibility': {'editor_pool': {'passed': True}},
                  'side_uv': {'editor_south': {'passed': True}}, 'lifecycle': {},
                  'maximum_observed_groups': 8, 'passed': False}
        world = {'evidence_valid': True, 'visibility': {'full_pool': {'passed': True}},
                 'side_uv': {'full_south': {'passed': True}}, 'lifecycle': {'full_pool': True},
                 'maximum_observed_groups': 8, 'passed': False}
        paths = [Path('editor.json'), Path('full.json')]
        reports = [{'owner_timing_ms': {'LiquidControls.update': [1.] * 20,
                                        'LiquidPreview.advance': [1.] * 20}},
                   {'owner_timing_ms': {'WorldLiquidRenderer.advance': [1.] * 20,
                                        'LiquidProjection.advance': [1.] * 20}}]
        with patch.object(qualification, 'replay', side_effect=[editor, world]), \
                patch.object(qualification, 'sha', return_value='0' * 64):
            self.assertTrue(qualification.frozen_matrix(paths, reports)['passed'])
        missing_owner = copy.deepcopy(reports)
        del missing_owner[1]['owner_timing_ms']['LiquidProjection.advance']
        with patch.object(qualification, 'replay', side_effect=[editor, world]), \
                patch.object(qualification, 'sha', return_value='0' * 64):
            self.assertFalse(qualification.frozen_matrix(paths, missing_owner)['passed'])
        world['evidence_valid'] = False
        with patch.object(qualification, 'replay', side_effect=[editor, world]), \
                patch.object(qualification, 'sha', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'Invalid completed frozen water report'):
                qualification.frozen_matrix(paths, reports)

    def test_duplicate_route_samples_and_failed_visibility_do_not_pass(self):
        observed = {'evidence_valid': True, 'visibility': {'editor_pool': {'passed': False}},
                    'side_uv': {'editor_south': {'passed': True}}, 'lifecycle': {'full_pool': True},
                    'maximum_observed_groups': 8}
        reports = [{'owner_timing_ms': {'LiquidControls.update': [1.] * 20}}]
        with patch.object(qualification, 'replay', return_value=observed), \
                patch.object(qualification, 'sha', return_value='0' * 64):
            self.assertFalse(qualification.frozen_matrix([Path('editor.json')], reports)['passed'])
            with self.assertRaisesRegex(ValueError, 'duplicate display-route cases'):
                qualification.frozen_matrix([Path('editor.json'), Path('copy.json')], reports * 2)


if __name__ == '__main__':
    unittest.main()
