"""Frozen startup failure cannot become door or capture acceptance evidence."""
import base64
import hashlib
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / 'tools/data/native_single_door_startup_r11_v11'


class FrozenSingleDoorStartupTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((DATA / 'manifest.json').read_bytes())
        self.report = json.loads((DATA / 'supervisor.json').read_bytes())

    def test_frozen_raw_sources_and_observations_match_the_manifest_exactly(self):
        expected = set(self.manifest['files']) | {'manifest.json'}
        self.assertEqual(expected, {path.name for path in DATA.iterdir() if path.is_file()})
        for name, digest in self.manifest['files'].items():
            with self.subTest(name=name):
                self.assertEqual(digest, hashlib.sha256((DATA / name).read_bytes()).hexdigest())
        launch = self.report['phases'][0]
        self.assertEqual((DATA / 'launcher.stdout').read_bytes(), base64.b64decode(launch['stdout_base64']))
        self.assertEqual(b'', base64.b64decode(launch['stderr_base64']))

    def test_failed_startup_did_not_execute_a_probe_or_verify_fixture_capture_or_orientation(self):
        self.assertFalse(self.report['ok'])
        self.assertEqual(1, self.report['launches'])
        self.assertEqual(['launch', 'normal_stop', 'force_stop'], [row['label'] for row in self.report['phases']])
        self.assertTrue(self.report['within_total_limit'])
        self.assertLess(self.report['elapsed_seconds'], 150)
        self.assertFalse(self.report['diagnosis']['mutation_attempted'])
        for key in ('ready', 'door_probe_executed', 'data_replication_verified',
                    'client_typed_pair_verified', 'physical_orientation_accepted', 'capture_reliable'):
            with self.subTest(key=key):
                self.assertFalse(self.manifest[key])
        self.assertEqual('not_attempted_before_readiness', self.manifest['capture_status'])
        self.assertEqual('not_applicable_no_fixture_mutation', self.manifest['fixture_restoration'])
        launch = json.loads((DATA / 'launcher.stdout').read_bytes())
        self.assertFalse(launch['ready'])
        self.assertEqual(11, launch['discovery_timeouts'][0]['attempt'])
        self.assertEqual(launch['error'], launch['discovery_timeouts'][0]['error'])
        self.assertTrue(launch['noactivation']['background_safe'])
        self.assertTrue(launch['foreground_unchanged'])

    def test_exact_owned_absence_and_launch_input_restoration_remain_distinct_from_later_code_fix(self):
        self.assertEqual([], self.report['cleanup_errors'])
        self.assertTrue(self.report['owned_processes_absent'])
        self.assertEqual({'game': None, 'mcdk': None}, self.report['identities_after_stop'])
        self.assertTrue(all(row['restored'] for row in self.report['inputs']))
        audit = json.loads((DATA / 'cleanup-audit.json').read_bytes())
        self.assertIsNone(audit['owned_game']['observed_identity'])
        self.assertIsNone(audit['owned_mcdk']['observed_identity'])
        self.assertEqual(audit['frame']['expected_identity'], audit['frame']['observed_identity'])
        self.assertFalse(audit['config_present'])
        self.assertFalse(audit['later_authorized_launcher_edit']['native_executed'])


if __name__ == '__main__':
    unittest.main()
