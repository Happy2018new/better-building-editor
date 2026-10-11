"""Ordered world mutations and interrupted glass cleanup stay independent."""
from argparse import Namespace
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_pot_isolation as probe


class NativePotIsolationTests(unittest.TestCase):
    def test_glass_round_trip_precedes_fresh_setter_and_palette_controls(self):
        report = {'controls': {}, 'events': [], 'mutations': []}
        args = Namespace(fixture_y=90, weather_settle=0, offset=(0., .4, 4.),
                         timeout=1, replication_timeout=1, vertical_fov=66.5)
        check = Mock()
        check.run.return_value = {'cold': True}
        operations = []
        captured = []

        def execute(client, code):
            compile(code, '<server-isolation>', 'exec')
            if code.startswith(probe.cold.SETUP.split('height=')[0]):
                return {'targets': {'item': (8,90,8), 'set_block': (12,90,8)}}
            if 'key,method=' in code:
                return {'returned': True}
            if 'key,operation=' in code:
                operations.append(code.split('key,operation=')[1].splitlines()[0])
            if 'key,sherds=' in code:
                operations.append('fixture_nbt')
            return {}

        def snapshot(check, report, output, args, key, label, expected=None):
            captured.append(label)
            stage = {'body': {'positive_control_passed': True}}
            report['controls'][key]['stages'][label] = stage
            return stage

        with patch.object(probe, 'execute', side_effect=execute), \
                patch.object(probe, 'snapshot', side_effect=snapshot), \
                patch.object(probe.cold, 'capture_stage', return_value={}), \
                patch.object(probe.time, 'sleep'):
            probe.run_probe(check, report, Path('unused.json'), args)

        self.assertEqual(["'item','glass_add'", "'item','glass_remove'",
                          "'set_block','fresh_native'", "'set_block','state_only'",
                          "'set_block','fresh_native'", "'set_block','liquid_air_only'",
                          "'set_block','palette_no_extra'", "'set_block','palette_extra_air'",
                          'fixture_nbt', "'set_block','production_fixture'"], operations)
        self.assertEqual('item_untouched_native', captured[0])
        self.assertEqual('set_block_untouched_native', captured[1])
        self.assertTrue(report['completed'])
        self.assertTrue(report['glass_remove_restored_body'])

    def test_cleanup_reservation_is_installed_and_restored_after_failure(self):
        original = probe.cold.RESTORE_WORLD

        def cleanup(check, report):
            self.assertIn("for pos in saved['reserved']:", probe.cold.RESTORE_WORLD)
            raise RuntimeError('injected IPC failure')

        with patch.object(probe.cold, 'cleanup', side_effect=cleanup):
            with self.assertRaisesRegex(RuntimeError, 'injected IPC failure'):
                probe.cleanup(Mock(), {})
        self.assertIs(original, probe.cold.RESTORE_WORLD)

    def test_generated_server_and_client_fragments_compile(self):
        for operation in ('glass_add', 'glass_remove', 'state_only', 'liquid_air_only',
                          'palette_no_extra', 'palette_extra_air', 'production_fixture'):
            compile(probe.MUTATE % ('item', operation), '<mutation>', 'exec')
        compile(probe.READ_SERVER % 'item', '<server-read>', 'exec')
        compile(probe.RESTORE_WORLD, '<world-restore>', 'exec')
        compile(probe.cold.CLIENT + probe.cold.READ_CLIENT % ((8,90,8), None), '<client-read>', 'exec')


if __name__ == '__main__':
    unittest.main()
