"""Preserve V12 invalid-anchor observations without promoting door acceptance."""
import base64
import hashlib
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / 'tools/data/native_single_door_load_failure_r11_v12'


class FrozenSingleDoorLoadFailureTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((DATA / 'manifest.json').read_bytes())
        self.supervisor = json.loads((DATA / 'supervisor.json').read_bytes())
        self.probe = json.loads((DATA / 'probe.json').read_bytes())

    def test_original_bytes_and_inventory_match_frozen_manifest(self):
        self.assertEqual(set(self.manifest['files']) | {'manifest.json'},
                         {path.name for path in DATA.iterdir() if path.is_file()})
        for name, digest in self.manifest['files'].items():
            with self.subTest(name=name):
                self.assertEqual(digest, hashlib.sha256((DATA / name).read_bytes()).hexdigest())
        launch = self.supervisor['phases'][0]
        self.assertEqual((DATA / 'launch-original.json').read_bytes(),
                         base64.b64decode(launch['stdout_base64']))
        self.assertEqual(b'', base64.b64decode(launch['stderr_base64']))
        self.assertEqual(hashlib.sha256((DATA / 'probe_native_single_door.py').read_bytes()).hexdigest(),
                         self.probe['host_sources']['probe']['sha256'])

    def test_unsettled_raw_anchor_and_refused_support_do_not_establish_door_evidence(self):
        self.assertEqual([.5, 32768., .5], self.probe['preflight']['foot'])
        self.assertEqual([4, 32780, 4], self.probe['preflight']['origin'])
        self.assertEqual(0, self.probe['preflight']['dimension'])
        support = self.probe['setup']['support_write']
        self.assertEqual([4, 32779, 4], support['pos'])
        self.assertIs(False, support['returned'])
        self.assertEqual({'name': 'minecraft:air', 'aux': 0}, support['value'])
        self.assertIsNone(support['states'])
        self.assertEqual('AssertionError: Support not stone', self.probe['setup']['error'])
        self.assertEqual([], self.probe['setup']['steps'])
        self.assertEqual(2, len(self.probe['setup']['after']['rows']))
        for row in self.probe['setup']['after']['rows']:
            self.assertEqual({'name': 'minecraft:air', 'aux': 0}, row['value'])
            self.assertIsNone(row['states'])
        for key in ('after_200ms', 'later', 'diagnosis'):
            self.assertNotIn(key, self.probe)
        launch = json.loads((DATA / 'launch-original.json').read_bytes())
        self.assertTrue(launch['ready'])
        for key in ('completed', 'server_exact_native_pair', 'data_replication_verified',
                    'client_typed_pair_verified', 'physical_orientation_accepted'):
            self.assertFalse(self.probe[key])
        for key in ('screenshot_attempted', 'capture_reliable', 'physical_orientation_accepted'):
            self.assertFalse(self.manifest[key])

    def test_cleanup_and_process_absence_remain_distinct_from_fixture_readiness(self):
        self.assertFalse(self.supervisor['ok'])
        self.assertEqual(['launch', 'probe', 'normal_stop', 'force_stop'],
                         [row['label'] for row in self.supervisor['phases']])
        self.assertTrue(self.probe['mutation_attempted'])
        self.assertTrue(self.probe['restored'])
        self.assertTrue(self.probe['cleanup']['player_unchanged'])
        self.assertEqual([], self.probe['cleanup']['errors'])
        self.assertEqual(17, len(self.probe['client_after_cleanup']['rows']))
        self.assertTrue(all(row['value'] == ['minecraft:air', 0]
                            for row in self.probe['client_after_cleanup']['rows']))
        self.assertEqual([], self.supervisor['cleanup_errors'])
        self.assertTrue(all(row['restored'] for row in self.supervisor['inputs']))
        self.assertTrue(self.supervisor['owned_processes_absent'])
        self.assertTrue(self.supervisor['within_total_limit'])
        audit = json.loads((DATA / 'cleanup-audit.json').read_bytes())
        self.assertIsNone(audit['owned_game']['observed_identity'])
        self.assertIsNone(audit['owned_mcdk']['observed_identity'])
        self.assertEqual(audit['frame']['expected_identity'], audit['frame']['observed_identity'])
        self.assertFalse(audit['frame']['sdk_or_input_called'])
        self.assertFalse(audit['config_present'])
        self.assertFalse(audit['fixture']['reserve_coordinates_in_world_bounds'])


if __name__ == '__main__':
    unittest.main()
