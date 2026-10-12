"""Bind retained R11 evidence bytes and scope without accessing host artifacts."""
import hashlib
import json
from pathlib import Path
import unittest


DATA = Path(__file__).resolve().parents[1] / 'tools/data'
EXPECTED = {
    'plant-position-native-evidence-r11-v1.json':
        '2ecc660c60dba961a637b9fd10e2a00c591a4a7a9f4fcc4bf6bdf4142bc76e5b',
    'plant-position-native-evidence-r11-v2.json':
        '8a8fcc2782cc9413bf90c997917833f9712bcbc5a7355bceeb248d1feec1c9dc',
}
CALIBRATION = {(-47, 117, -70), (6, 117, 6), (7, 117, 6), (6, 117, 7)}
SESSIONS = {
    '8c6723d6a08f49af9464f1e23bea232c',
    '22852a6c89374b79a7d16f75ca8c94c1',
    'dd24458e830443f583aa49c6fbc01845',
    '517f7c483aa647e784ccdb37bab9bc45',
}
ALPHA_SHA = '7060164de76ea6e3de651a42f4a6dfbdae27dc4d86daccbd5f7b1807fce1008c'


class PlantPositionEvidenceR11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = {name: (DATA / name).read_bytes() for name in EXPECTED}
        cls.reports = {name: json.loads(raw) for name, raw in cls.raw.items()}

    def test_original_report_bytes_are_frozen(self):
        for name, raw in self.raw.items():
            with self.subTest(report=name):
                self.assertEqual(EXPECTED[name], hashlib.sha256(raw).hexdigest())

    def test_original_baseline_contains_only_eight_predeclared_calibration_views(self):
        expected = {(target, view) for target in CALIBRATION for view in ('public', 'right')}
        for name, report in self.reports.items():
            with self.subTest(report=name):
                rows = report['baseline']['rows']
                self.assertEqual(8, len(rows))
                self.assertEqual(expected, {(tuple(row['target']), row['view']) for row in rows})
                self.assertEqual([row['shown'] for row in rows], report['viewed_native_pngs'])
                self.assertEqual(-1, report['baseline']['graphics_state']['options']['GRAPHICS'])
                for row in rows:
                    self.assertEqual({'name': 'minecraft:poppy', 'aux': 0}, row['readback']['front'])
                    self.assertEqual(row['target'], row['readback']['target'])
                    self.assertEqual('plant', row['readback']['kind'])
                    self.assertEqual(0, row['readback']['height'])
                    self.assertGreater(row['diagnostic_pixels'], 0)

    def test_failures_and_frozen_content_do_not_become_native_progress(self):
        for name, report in self.reports.items():
            with self.subTest(report=name):
                failed = report['marker_retry_camera_failure']
                self.assertIs(False, failed['mutation_started'])
                self.assertIn('execute_code returned no value', failed['error'])
                frozen = report['marker_retry_frozen_content_capture']
                self.assertIs(False, frozen['live_render_progress_proven'])
                self.assertEqual('2026-10-12T21:30:39+08:00', frozen['embedded_local_time'])
                self.assertEqual('2026-10-12T21:35:45+08:00', frozen['capture_time'])
                sessions = {row['session_id']: row for row in report['sessions']}
                self.assertEqual(SESSIONS, set(sessions))
                first_marker = sessions['22852a6c89374b79a7d16f75ca8c94c1']
                self.assertEqual('failed', first_marker['state'])
                self.assertEqual('Owned game violated the noactivation window contract', first_marker['error'])
                for session in sessions.values():
                    self.assertEqual('snow-r11-position', session['owner'])
                    self.assertIs(True, session['processes_dead'])
                    self.assertIs(False, session['ready'])

    def test_restoration_and_alpha_preservation_remain_recorded(self):
        for name, report in self.reports.items():
            with self.subTest(report=name):
                restored = report['baseline']['restoration']
                self.assertEqual(CALIBRATION, {tuple(row['target']) for row in restored})
                self.assertEqual(4, len(restored))
                for group in restored:
                    self.assertTrue(group['results'])
                    for result in group['results']:
                        self.assertIs(True, result['clean'])
                snapshots = report['alpha_marker_snapshots']
                self.assertEqual(2, len(snapshots))
                for snapshot in snapshots:
                    self.assertEqual(ALPHA_SHA, snapshot['native_alpha_sha256'])
                    self.assertEqual(ALPHA_SHA, snapshot['candidate_alpha_sha256'])
                    self.assertIs(True, snapshot['restored_override_absent'])

    def test_diagnostic_evidence_does_not_expand_accepted_rendering_scope(self):
        scope = {'positive_states': 29, 'height_observations': 232,
                 'negative_lower_half_states': 8,
                 'seed_name_false_rows_are_observed_negatives': False}
        for name, report in self.reports.items():
            with self.subTest(report=name):
                self.assertEqual(1, report['schema'])
                for flag in ('production_acceptance', 'native_mesh_authority_recovered',
                             'native_offset_formula_recovered'):
                    self.assertIs(False, report[flag])
                self.assertEqual(scope, report['accepted_scope_unchanged'])
                self.assertIn('No holdout pixels were acquired or used for fitting', report['limits'])
                self.assertIn('No alpha-marker geometry frame was accepted; no opaque marker was installed',
                              report['limits'])
                self.assertIn('Production position registry remains empty; original pixel gates remain unchanged',
                              report['limits'])

    def test_v2_adds_camera_binding_without_replacing_v1_observations(self):
        first = self.reports['plant-position-native-evidence-r11-v1.json']
        second = self.reports['plant-position-native-evidence-r11-v2.json']
        calibration = second['baseline']['camera_calibration']
        self.assertEqual('9c20828a684ef41dfdead0741852d9059aab3c26d28eaaadd953fd94b45267b5',
                         calibration['sha256'])
        without_camera = dict(second['baseline'])
        del without_camera['camera_calibration']
        self.assertEqual(first['baseline'], without_camera)
        for key in first:
            if key != 'baseline':
                self.assertEqual(first[key], second[key], key)


if __name__ == '__main__':
    unittest.main()
