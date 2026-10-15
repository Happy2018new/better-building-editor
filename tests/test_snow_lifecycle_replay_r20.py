"""Verify lifecycle replay against preserved native pixels and corrupted receipts."""
import copy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_snow_lifecycle_r20 import analyze
from run_snow_scene_lifecycle_r20 import snow_control_checks
from verify_centered_snow_profiles import save_mask
from verify_snow_package_r20 import remap
from verify_snow_plant_visibility import capture_frame, editor_snow_geometry


class SnowLifecycleReplayR20Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This is a replay adapter for old controls, not a new native workflow claim.
        cls.temporary = TemporaryDirectory(prefix='snow-lifecycle-replay-')
        cls.addClassCleanup(cls.temporary.cleanup)
        package = ROOT / 'docs/evidence/snow-product-r20-v1'
        manifest = json.loads((package / 'manifest.json').read_bytes())
        original = remap(json.loads((package / 'matrix/report.json').read_bytes()),
                         manifest['original_to_package'], package)
        selected = {kind: next(row for row in original['rows'] if row['kind'] == kind
                              and (kind in ('blank', 'plant') or row['height'] == 4))
                    for kind in ('blank', 'plant', 'snow', 'covered')}
        capture = selected['blank']['editor']['capture']
        cls.report = {'owner': capture['owner'], 'game_pid': capture['game_pid'],
            'game_identity': capture['game_identity'], 'completed': False, 'passed': False,
            'restored': False, 'cleanup_errors': ['Unit replay adapter; no native editing acquisition'],
            'height': 4, 'editor_crop': selected['blank']['editor_crop'],
            'assets': original['assets']['blue_orchid'],
            'native_draw_preflight': original['native_draw_preflight'], 'steps': [], 'controls': {}}
        for kind, row in selected.items():
            control = {'screenshot': row['editor'], 'source': row['source'],
                       'camera_state': row['camera_state'], 'native_response': row['native_editor_response'],
                       'passed': True, 'checks': {'passed': True, 'expected_empty': True}}
            if kind == 'plant':
                control.update(expected_alpha=row['editor_expected_alpha'], checks=row['checks']['editor_shape'])
            elif kind == 'snow':
                frame = capture_frame(row['editor']['path'], row['editor_crop'], selected['blank']['editor']['path'])
                geometry = editor_snow_geometry(row['editor_crop'], row['camera_state'], row['source']['focus'], 4)[0]
                control.update(expected_alpha=save_mask(geometry, Path(cls.temporary.name) / 'adapter.json', 'snow'), checks=snow_control_checks(
                    row['editor_crop'], row['camera_state'], row['source']['focus'], 4, frame['object']))
            elif kind == 'covered':
                control['checks'] = row['checks']['editor_snow']
            cls.report['controls'][kind] = control

    def test_actual_controls_replay_but_cannot_accept_incomplete_workflow_or_missing_crop(self):
        replay = analyze(self.report)
        self.assertTrue(replay['pixels_replayed'])
        self.assertTrue(all(row['passed'] for row in replay['controls'].values()))
        self.assertFalse(replay['workflow_accepted'])
        self.assertFalse(replay['production_accepted'])
        legacy = copy.deepcopy(self.report)
        del legacy['editor_crop']
        legacy.update(completed=True, restored=True, passed=True, cleanup_errors=[])
        partial = analyze(legacy)
        self.assertTrue(partial['capture_bytes_verified'])
        self.assertFalse(partial['pixels_replayed'])
        self.assertFalse(partial['workflow_accepted'])
        self.assertIn('Scene editor crop', partial['replay_blockers'][0])

    def test_rejects_changed_owner_tick_clock_or_alpha(self):
        for corrupted in ('owner', 'ticks', 'clock', 'response_capture', 'alpha'):
            report = copy.deepcopy(self.report)
            row = report['controls']['plant']
            if corrupted == 'owner':
                row['screenshot']['capture']['owner'] = 'another-owner'
            elif corrupted == 'ticks':
                ticks = row['native_response']['attempts'][0]['render_frames']
                ticks['after'] = ticks['before']
            elif corrupted == 'clock':
                row['native_response']['reference_clock']['sha256'] = 'forged'
            elif corrupted == 'response_capture':
                row['native_response']['attempts'][-1]['capture'] = report['controls']['snow']['screenshot']
            else:
                row['expected_alpha'] = report['controls']['snow']['expected_alpha']
            with self.subTest(corrupted=corrupted), self.assertRaises(ValueError):
                analyze(report)


if __name__ == '__main__':
    unittest.main()
