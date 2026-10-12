"""Validate the portable failed-startup archive without a game or host files."""
import hashlib
import json
from pathlib import Path
import unittest

ARCHIVE = Path(__file__).resolve().parents[1]/'tools/data/plant-alpha-single-startup-r11-v3'
INDEX_SHA = '6110beaaacff545e5bcf0afcfdef81017d9605bf9c991e5d6b32002ea67d0d53'


class PlantAlphaStartupEvidenceR11Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = json.loads((ARCHIVE/'index.json').read_bytes())
        cls.supervisor = json.loads((ARCHIVE/'supervisor.json').read_bytes())
        cls.failed = json.loads((ARCHIVE/'sources/launch-failed-original.json').read_bytes())
        cls.binding = json.loads((ARCHIVE/'failure-binding.json').read_bytes())

    def test_index_and_all_raw_archived_bytes_are_frozen(self):
        self.assertEqual(INDEX_SHA, hashlib.sha256((ARCHIVE/'index.json').read_bytes()).hexdigest())
        files = self.index['files']
        self.assertEqual(37, len(files))
        for relative, expected in files.items():
            with self.subTest(file=relative):
                path = (ARCHIVE/relative).resolve()
                self.assertTrue(path.is_relative_to(ARCHIVE.resolve()))
                raw = path.read_bytes()
                self.assertEqual(expected['sha256'], hashlib.sha256(raw).hexdigest())
                self.assertEqual(expected['bytes'], len(raw))

    def test_one_launch_failed_before_any_health_fixture_or_capture_stage(self):
        for flag in ('health_stage_started','timer_stage_started','camera_stage_started',
                     'fixture_stage_started','capture_stage_started','marker_pixels_observed'):
            self.assertIs(False, self.index[flag])
        self.assertEqual(1, self.supervisor['launches'])
        self.assertEqual(['launch'], [phase['label'] for phase in self.supervisor['phases']])
        phase = self.supervisor['phases'][0]
        self.assertEqual((ARCHIVE/'sources/launch-failed-original.json').read_bytes(),
                         phase['stdout'].encode('utf8'))
        self.assertEqual(1, phase['returncode'])
        self.assertIs(False, phase['timeout'])
        self.assertIs(False, self.supervisor['observation_completed'])
        self.assertIs(False, self.failed['ready'])
        self.assertEqual('failed', self.failed['state'])
        error = json.loads(self.failed['error'])
        self.assertIs(True, error['isError'])
        self.assertEqual('Code execution failed. The player may not be in the game or the target is unavailable.',
                         error['content'][0]['text'])
        self.assertEqual(150, self.supervisor['total_run_timeout_seconds'])
        self.assertLess(self.supervisor['run_elapsed_seconds'], 150)

    def test_bound_owned_cleanup_and_original_bytes_are_retained(self):
        stopped = json.loads((ARCHIVE/'session-stopped.json').read_bytes())
        self.assertEqual('stopped', stopped['state'])
        self.assertIs(False, stopped['ready'])
        self.assertEqual('f67b34e0b2c442a594780b64d8b7b32d', stopped['id'])
        self.assertEqual('snow-r11-position', stopped['owner'])
        self.assertEqual((11260,'134362917459245243'), (stopped['game_pid'],stopped['game_identity']))
        self.assertEqual((26396,'134362917457212643'), (stopped['mcdk_pid'],stopped['mcdk_identity']))
        self.assertIs(True, self.supervisor['owned_processes_dead'])
        self.assertEqual({'game':True,'mcdk':True}, self.binding['processes_dead'])
        self.assertEqual([], self.supervisor['cleanup_errors'])
        self.assertEqual(1, self.supervisor['normal_stop']['returncode'])
        self.assertEqual(['game','mcdk'], self.supervisor['force_stop_after_inspection']['live_owned_kinds'])
        self.assertEqual(0, self.supervisor['force_stop_after_inspection']['result']['returncode'])
        self.assertIs(True, self.supervisor['marker_override_absent'])
        self.assertIs(True, self.supervisor['native_texture_unchanged'])
        for row in self.supervisor['backup']:
            self.assertIs(True, row['restored'])
            name = Path(row['backup']).name
            self.assertEqual(row['sha256'], hashlib.sha256((ARCHIVE/'original-bytes'/name).read_bytes()).hexdigest())

    def test_alpha_source_and_cold_flat_config_are_preserved(self):
        from PIL import Image
        snapshot = json.loads((ARCHIVE/'marker-snapshot.json').read_bytes())
        self.assertEqual('native_alpha_preserved', snapshot['mode'])
        self.assertIsNone(snapshot['before_hex'])
        with Image.open(ARCHIVE/'native-original-poppy.png') as native, \
                Image.open(ARCHIVE/'alpha-candidate.png') as marker:
            self.assertEqual((16,16), marker.size)
            native_alpha = native.convert('RGBA').getchannel('A').tobytes()
            marker_alpha = marker.convert('RGBA').getchannel('A').tobytes()
            self.assertEqual(native_alpha, marker_alpha)
            self.assertEqual(snapshot['native_alpha_sha256'], hashlib.sha256(native_alpha).hexdigest())
            self.assertEqual(snapshot['candidate_alpha_sha256'], hashlib.sha256(marker_alpha).hexdigest())
        for filename in ('sources/private-flat-creative.mcdev.json','generated-instance.mcdev.json'):
            config = json.loads((ARCHIVE/filename).read_bytes())
            self.assertEqual(2, config['world_type'])
            self.assertEqual(0, config['world_seed'])
            self.assertEqual(1, config['game_mode'])
            for key in ('auto_hot_reload_mods','auto_hot_reload_ui','auto_hot_reload_shaders','auto_hot_reload_materials'):
                self.assertIs(False, config[key])
        plan = json.loads((ARCHIVE/'independent-plan.json').read_bytes())
        self.assertEqual(plan['texture_source']['sha256'],
                         hashlib.sha256((ARCHIVE/'native-original-poppy.png').read_bytes()).hexdigest())

    def test_failure_remains_separate_from_rendering_acceptance(self):
        for flag in ('production_acceptance','native_mesh_authority_recovered','native_offset_formula_recovered'):
            self.assertIs(False, self.index[flag])
            self.assertIs(False, self.binding[flag])
        self.assertEqual({'positive_states':29,'height_observations':232,'negative_lower_half_states':8,
                          'seed_name_false_rows_are_observed_negatives':False}, self.index['accepted_scope_unchanged'])
        mapping = self.index['ready_failure_source_mapping']
        self.assertEqual(0, mapping['connected_debug_ipc_clients_at_failed_read'])
        self.assertIs(False, mapping['requestJsonValue_reached'])
        self.assertIs(False, mapping['cause_of_zero_connections_recovered'])
        source = (ARCHIVE/mapping['source_file']).read_text(encoding='utf8').splitlines()
        self.assertIn(mapping['condition'], source[mapping['line']-1])


if __name__=='__main__':
    unittest.main()
