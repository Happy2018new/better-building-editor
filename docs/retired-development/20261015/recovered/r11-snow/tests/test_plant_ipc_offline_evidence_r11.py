"""Validate the frozen comparison and its limits without host runtime access."""
import hashlib
import json
from pathlib import Path
import unittest

ARCHIVE = Path(__file__).resolve().parents[1] / 'tools/data/plant-ipc-offline-r11-v1'
INDEX_SHA = 'f4686f31985c5f4adc1a23f0265a5422bb71deba3a90640a2788e357b694952b'


class PlantIPCOfflineEvidenceR11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ARCHIVE / 'index.json').read_bytes())
        cls.report = json.loads((ARCHIVE / 'comparison.json').read_bytes())
        cls.analysis = json.loads((ARCHIVE / 'analysis.json').read_bytes())
        cls.plan = json.loads((ARCHIVE / 'passive-startup-plan.json').read_bytes())

    def test_complete_portable_archive_preserves_raw_bytes(self):
        self.assertEqual(INDEX_SHA, hashlib.sha256((ARCHIVE / 'index.json').read_bytes()).hexdigest())
        self.assertEqual(76, len(self.index['files']))
        for relative, record in self.index['files'].items():
            with self.subTest(file=relative):
                path = (ARCHIVE / relative).resolve()
                self.assertTrue(path.is_relative_to(ARCHIVE.resolve()))
                raw = path.read_bytes()
                self.assertEqual(record['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(record['bytes'], len(raw))

    def test_all_debug_files_match_all_three_receipts_and_archived_bytes(self):
        trees = self.report['debug_trees']
        self.assertEqual(17, len(trees['failed']))
        self.assertEqual(trees['healthy'], trees['failed'])
        self.assertEqual(trees['installed'], trees['failed'])
        for relative, digest in trees['failed'].items():
            self.assertEqual(digest, hashlib.sha256((ARCHIVE / 'generated-debug' / relative).read_bytes()).hexdigest())
        self.assertEqual(17, self.report['generated_debug_comparison']['matching_count'])
        self.assertEqual({}, self.report['generated_debug_comparison']['different'])

    def test_config_and_world_metadata_differences_are_reproducible_offline(self):
        configs = {label: json.loads((ARCHIVE / label / 'mcdev.json').read_bytes())
                   for label in ('healthy', 'failed')}
        actual = {key: {'healthy': configs['healthy'].get(key), 'failed': configs['failed'].get(key)}
                  for key in sorted(set(configs['healthy']) | set(configs['failed']))
                  if configs['healthy'].get(key) != configs['failed'].get(key)}
        self.assertEqual(self.report['config_differences'], actual)
        for key in ('do_daylight_cycle', 'do_weather_cycle'):
            self.assertEqual({'healthy': False, 'failed': None}, actual[key])
        for label in ('healthy', 'failed'):
            world = self.report['worlds'][label]
            for kind in ('behavior_packs', 'resource_packs'):
                self.assertEqual(world['pack_lists'][kind],
                    json.loads((ARCHIVE / label / ('world_' + kind + '.json')).read_bytes()))
            for link in world['links']:
                raw = (ARCHIVE / label / 'world-manifests' / (link['name'] + '.json')).read_bytes()
                self.assertEqual(link['manifest_sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(link['manifest'], json.loads(raw))

    def test_zero_client_and_log_filter_mapping_are_bound_to_raw_source(self):
        for mapping in self.analysis['source_mapping'].values():
            with self.subTest(source=mapping['source'], line=mapping['line']):
                lines = (ARCHIVE / mapping['source']).read_text(encoding='utf8').splitlines()
                self.assertIn(mapping['contains'], lines[mapping['line'] - 1])
        mapping = self.analysis['source_mapping']
        self.assertEqual(204, mapping['zero_client_failure']['line'])
        self.assertLess(mapping['ipc_started']['line'], mapping['child_port_set']['line'])
        self.assertLess(mapping['child_port_set']['line'], mapping['explicit_child_env_built']['line'])
        self.assertLess(mapping['explicit_child_env_built']['line'], mapping['explicit_child_env_passed']['line'])
        failed_log = (ARCHIVE / 'failed/mcdk.log').read_text(encoding='utf8')
        self.assertEqual(0, sum('[Python]' in line for line in failed_log.splitlines()))
        self.assertIn('[MCDK] IPC Bridge listening on port 52115', failed_log)
        self.assertEqual(52115, self.analysis['failed_listener_port'])
        self.assertEqual(52112, self.analysis['failed_mcp_port'])
        self.assertIn('does not prove absence', self.analysis['logging_conclusion'])
        self.assertIn('not captured', self.analysis['environment_conclusion'])

    def test_project_differences_remain_post_cleanup_observations(self):
        observed = self.report['project_comparison_observed_after_failure_cleanup']
        self.assertIs(True, observed['not_a_controlled_prelaunch_source_equality_claim'])
        self.assertEqual(709, observed['resource']['matching_count'])
        self.assertEqual({}, observed['resource']['different'])
        self.assertEqual(7, len(observed['behavior']['different']))
        self.assertEqual(['modern_projection/projection/plant_position.py'], observed['behavior']['failed_only'])
        for relative, expected in observed['behavior']['different'].items():
            for label in ('healthy', 'failed'):
                self.assertEqual(expected[label], hashlib.sha256(
                    (ARCHIVE / label / 'current-behavior' / relative).read_bytes()).hexdigest())

    def test_passive_preparation_does_not_claim_runtime_or_rendering_success(self):
        self.assertEqual(0, self.index['native_launches_in_this_task'])
        self.assertEqual(0, self.index['native_observer_invocations_in_this_task'])
        for document in (self.report, self.analysis):
            self.assertIs(False, document['production_acceptance'])
            self.assertIs(False, document['game_or_window_accessed'])
            self.assertIs(False, document['mcp_or_private_ipc_connected'])
            self.assertIs(False, document['native_session_launched'])
            self.assertIs(False, document['zero_ipc_client_cause_recovered'])
            self.assertGreaterEqual(len(document['remaining_causes']), 5)
        self.assertEqual('prepared_for_root_review_not_run', self.plan['status'])
        self.assertEqual(0, self.plan['authorized_launches_in_this_offline_task'])
        budget = self.plan['future_bounds_proposed']
        self.assertEqual(1, budget['max_launches'])
        self.assertEqual(150, budget['total_external_supervisor_seconds'])
        self.assertEqual(150, budget['startup_observation_deadline_seconds'] + budget['reserved_cleanup_seconds'])
        self.assertIs(False, self.plan['observer']['standard_ready_loader_changed'])
        self.assertIs(False, self.plan['observer']['sdk_or_mcp_called_by_observer'])
        self.assertIs(False, self.plan['observer']['private_ipc_connection_attempted'])
        self.assertIs(False, self.plan['observer']['focus_resize_restore_input_fallback'])
        self.assertEqual({'positive_states': 29, 'height_observations': 232,
                          'negative_lower_half_states': 8, 'seed_name_false_rows_are_observed_negatives': False},
                         self.analysis['accepted_scope_unchanged'])


if __name__ == '__main__':
    unittest.main()
