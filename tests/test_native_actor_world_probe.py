"""Preserved native placement evidence survives offline report replay."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_native_actor_world_probe as probe


class NativeActorWorldProbeTests(unittest.TestCase):
    def tearDown(self):
        probe.PROBES.clear()

    def test_replay_preserves_three_write_metadata_and_body_evidence(self):
        controls = dict((method, {'cell_actor_pixels_above_16': {'keep': 0, 'occupied': 17},
                                 'mask': method + '_body.png'})
                        for method in ('palette', 'set_block', 'item'))
        placement = {'rows': [{'position': [2, 3, 4], 'native_aux': 0,
                               'nbt': {'id': {'__type__': 8, '__value__': 'DecoratedPot'}}}],
                     'slot_restored': True, 'rotation_restored': True}
        native = {'label': 'pot_isolated_side_world', 'completed': True, 'same_camera': True,
                  'palette_capture': {'path': 'palette.png', 'sha256': '1' * 64},
                  'set_block_capture': {'path': 'set_block.png', 'sha256': '2' * 64},
                  'item_capture': {'path': 'item.png', 'sha256': '3' * 64},
                  'set_block_placement': placement, 'item_placement': copy.deepcopy(placement),
                  'native_body_controls': controls}
        report = {'passed': False, 'restored': True,
                  'cases': [{'case': 'pot_isolated', 'views': {'side': {
            'empty': {'path': 'missing_empty.png'}, 'roi': {'keep': [], 'occupied': []}}}}],
                  'native_item_world_probes': [native]}
        preserved = copy.deepcopy(report['native_item_world_probes'])
        self.assertEqual([], probe.PROBES)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'replayed.json'
            probe.write_report(output, report)
            replayed = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual(preserved, replayed['native_item_world_probes'])
        self.assertEqual(preserved, report['native_item_world_probes'])

    def test_live_records_replace_older_report_records(self):
        probe.PROBES.append({'label': 'current', 'completed': False})
        report = {'passed': False, 'restored': True, 'cases': [],
                  'native_item_world_probes': [{'label': 'old'}]}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'live.json'
            probe.write_report(output, report)
            saved = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual([{'label': 'current', 'completed': False}], saved['native_item_world_probes'])

    def test_skipped_wet_sign_does_not_send_escape(self):
        check = Mock()
        check.run.return_value = (0, 0, 0)
        placement = {'rows': [{'skipped_native_write': True, 'position': [1, 2, 3],
                               'requested': [], 'placed': {'name': 'minecraft:standing_sign'}}]}
        with patch.object(probe.world, 'run', return_value=placement), \
                patch.object(probe.wet, 'replication', return_value={'matches': True}), \
                patch.object(probe, '_camera_capture', return_value=({'stable': {}}, {})), \
                patch.object(probe.native, 'camera_matches', return_value=True), \
                patch.object(probe.time, 'sleep'):
            probe.camera_capture(check, 'sign_adjacent_water_side_world', (0, 0, 0), (1, 0, 0), 'side')
        check.client.call.assert_not_called()
        self.assertTrue(probe.PROBES[0]['completed'])

    def test_before_nbt_capture_precedes_fixture_assignment_and_full_replication(self):
        events = []
        check = Mock()
        check.run.return_value = (0, 0, 0)
        check.wait.return_value = {'matches': True}
        placement = {'rows': [{'position': [1, 2, 3], 'requested': [],
                               'placed': {'name': 'minecraft:decorated_pot'}}]}

        def run(client, code):
            compile(code, '<native-probe>', 'exec')
            if 'method=' in code:
                self.assertIn('apply_fixture_nbt=False', code)
                events.append('place')
                return copy.deepcopy(placement)
            events.append('assign_fixture_nbt')
            return {'fixture_nbt_applied': True, 'rows': []}

        def capture(unused, label, keep, occupied, view):
            events.append('before_nbt_capture' if label.endswith('_before_nbt') else 'final_capture')
            return {'stable': {}}, {'path': label + '.png'}

        def replicated(*args, **kwargs):
            events.append('full_fixture_replication')
            return {'matches': True}

        with patch.object(probe, 'CAPTURE_BEFORE_NBT', True), \
                patch.object(probe.world, 'run', side_effect=run), \
                patch.object(probe.wet, 'replication', side_effect=replicated), \
                patch.object(probe, '_camera_capture', side_effect=capture), \
                patch.object(probe.native, 'camera_matches', return_value=True), \
                patch.object(probe.time, 'sleep'):
            probe.camera_capture(check, 'pot_isolated_side_world', (0, 0, 0), (1, 0, 0), 'side')
        expected = ['place', 'before_nbt_capture', 'assign_fixture_nbt',
                    'full_fixture_replication', 'final_capture']
        self.assertEqual(['final_capture'] + expected * 2, events)
        record = probe.PROBES[0]
        self.assertTrue(record['capture_before_nbt'])
        self.assertIn('set_block_before_nbt_capture', record)
        self.assertIn('item_before_nbt_capture', record)


if __name__ == '__main__':
    unittest.main()
