"""Keep original native receipts distinct from corrected offline pair scoring."""
import base64
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'tools/data/native_single_door_observed_r11_v13b'
MANIFEST_SHA = 'c1461810d748854e5454f857510e9d6267436faac4014d8f5d97b9f934e6bca1'
sys.path.insert(0, str(ROOT / 'tools'))
import replay_native_single_door_v13b as replay


class FrozenSingleDoorObservedV13bTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((DATA / 'manifest.json').read_bytes())
        self.supervisor = json.loads((DATA / 'supervisor.json').read_bytes())
        self.probe = json.loads((DATA / 'probe.json').read_bytes())

    def test_frozen_inventory_preserves_original_stdout_receipts_and_source_pins(self):
        self.assertEqual(MANIFEST_SHA, hashlib.sha256((DATA / 'manifest.json').read_bytes()).hexdigest())
        self.assertEqual(set(self.manifest['files']) | {'manifest.json'},
                         {path.name for path in DATA.iterdir() if path.is_file()})
        for name, expected in self.manifest['files'].items():
            with self.subTest(name=name):
                self.assertEqual(expected, hashlib.sha256((DATA / name).read_bytes()).hexdigest())
        self.assertEqual((DATA / 'launch-original.json').read_bytes(),
                         base64.b64decode(self.supervisor['phases'][0]['stdout_base64']))
        for key, filename in (('probe', 'probe_native_single_door.py'),
                              ('load_preflight', 'native_single_door_load_preflight.py'),
                              ('palette_freezer', 'palette_freezer.py'),
                              ('mcp_wrapper', 'input-1-used'), ('session_loader', '_session.py')):
            self.assertEqual(self.manifest['files'][filename], self.probe['host_sources'][key]['sha256'])
        self.assertEqual('054200070a8e653a4e9e0e76f026d7a986dd8db0698074765278434c3b70d37b',
                         self.manifest['files']['supervisor-used.py'])
        self.assertEqual((DATA / 'corrected-scorer.py').read_bytes(),
                         (ROOT / 'tools/probe_native_single_door.py').read_bytes())
        self.assertEqual((DATA / 'corrected-runner.py').read_bytes(),
                         (ROOT / 'tools/run_native_single_door.py').read_bytes())

    def test_load_gate_retains_invalid_reads_without_chunk_queries_then_accepts_stable_loaded_anchor(self):
        attempts = self.probe['load_preflight']['attempts']
        self.assertEqual(6, len(attempts))
        for attempt in attempts[:4]:
            self.assertEqual([.5, 32768., .5], attempt['raw_anchor']['foot'])
            self.assertEqual('foot_outside_fixed_scope', attempt['status'])
            self.assertNotIn('raw_chunks', attempt)
        for attempt in attempts[4:]:
            self.assertEqual([.5, -60., .5], attempt['raw_anchor']['foot'])
            self.assertTrue(attempt['raw_chunks']['same_anchor'])
            self.assertTrue(all(row['loaded'] is True for row in attempt['raw_chunks']['chunks']))
        self.assertGreaterEqual(attempts[-1]['started_seconds'] - attempts[-2]['started_seconds'], .25)
        self.assertTrue(self.probe['load_preflight']['ready'])
        self.assertEqual([4, -48, 4], self.probe['preflight']['origin'])
        self.assertTrue(all(-64 <= pos[1] < 320 for pos in self.probe['reserved']))

    def test_original_observed_pair_and_failed_host_verdict_are_both_preserved(self):
        self.assertTrue(self.probe['setup']['support_write']['returned'])
        self.assertEqual([True, False, True, True], [row['returned'] for row in self.probe['setup']['steps']])
        self.assertTrue(self.probe['server_exact_native_pair'])
        self.assertFalse(self.probe['data_replication_verified'])
        self.assertFalse(self.supervisor['ok'])
        for stage in ('after_200ms', 'later'):
            observation = self.probe[stage]
            self.assertTrue(replay.corrected.shapes.replicated(observation['server'], self.probe['requested']))
            expected = [['minecraft:wooden_door', 0], ['minecraft:wooden_door', 8], ['minecraft:stone', 0]]
            for fronts in ('fronts_before', 'fronts_after'):
                self.assertEqual(expected, [row['value'] for row in observation['client'][fronts]])
            self.assertEqual('pair_palette_invalid', self.probe['diagnosis'][stage]['classification'])
            raw = replay.corrected.thaw(observation['client']['palettes']['pair']['serialized'])
            self.assertIsNone(raw.get('volume'))
            self.assertEqual((1, 1, 2), raw[b'volume'])
            self.assertFalse(observation['client']['palettes']['upper']['available'])

    def test_offline_replay_recovers_lower_typed_replication_without_native_calls_or_upper_synthesis(self):
        with mock.patch.object(replay.corrected, 'DeadlineClient') as client, \
             mock.patch.object(replay.corrected.shapes, 'load_session') as load_session, \
             mock.patch.object(replay.corrected.shapes, 'execute') as execute:
            result = replay.replay(DATA)
        client.assert_not_called()
        load_session.assert_not_called()
        execute.assert_not_called()
        self.assertTrue(result['original_bytes_unchanged'])
        self.assertTrue(result['data_replication_verified_from_existing_observations'])
        saved = json.loads((DATA / 'offline-replay.json').read_bytes())
        self.assertEqual(saved, json.loads(json.dumps(result)))
        for observation in result['observations'].values():
            self.assertTrue(observation['original_diagnosis_reproduced'])
            diagnosis = observation['corrected_offline_diagnosis']
            self.assertEqual('documented_upper_omission_observed', diagnosis['classification'])
            self.assertEqual([0], diagnosis['palette_covered_indices'])
            self.assertEqual([1], diagnosis['palette_omitted_indices'])
            self.assertFalse(diagnosis['client_typed_upper_verified'])
            self.assertFalse(diagnosis['physical_orientation_accepted'])
            self.assertEqual(1, len(observation['observed_palette_rows']))
        for key in ('physical_orientation_accepted', 'client_typed_pair_verified', 'capture_reliable',
                    'production_mapping_changed'):
            self.assertFalse(result[key])
        self.assertEqual(0, result['new_native_calls'] + result['new_sdk_calls'] + result['new_launches'])

    def test_owned_cleanup_inputs_and_protected_identity_are_verified_independently(self):
        audit = json.loads((DATA / 'cleanup-audit.json').read_bytes())
        self.assertEqual(1, self.supervisor['launches'])
        self.assertTrue(self.supervisor['within_total_limit'])
        self.assertLess(self.supervisor['elapsed_seconds'], 240)
        self.assertEqual(['launch', 'probe', 'normal_stop', 'force_stop'],
                         [row['label'] for row in self.supervisor['phases']])
        self.assertTrue(self.probe['restored'])
        self.assertTrue(self.probe['cleanup']['player_unchanged'])
        self.assertEqual([], self.probe['cleanup']['errors'])
        self.assertEqual(17, len(self.probe['client_after_cleanup']['rows']))
        self.assertTrue(all(row['value'] == ['minecraft:air', 0]
                            for row in self.probe['client_after_cleanup']['rows']))
        for key in ('owned_processes_independently_absent', 'frame_identity_unchanged',
                    'foreground_unchanged', 'launch_inputs_restored'):
            self.assertTrue(audit[key])
        self.assertTrue(all(row['observed_identity'] is None for row in audit['owned_processes'].values()))
        self.assertFalse(audit['frame']['sdk_or_input_called'])
        self.assertEqual([], self.supervisor['cleanup_errors'])
        self.assertTrue(all(row['restored'] for row in self.supervisor['inputs']))
        self.assertFalse(self.manifest['physical_orientation_accepted'])
        self.assertFalse(self.manifest['resource_stability_accepted'])


if __name__ == '__main__':
    unittest.main()
