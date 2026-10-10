"""Cold controls remain independent when fixture NBT replication mismatches."""
from argparse import Namespace
import copy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_cold_native_actor as probe


class ColdNativeActorProbeTests(unittest.TestCase):
    def test_both_raw_captures_precede_nbt_and_mismatches_do_not_stop_captures(self):
        report = {'controls': {}}
        check = Mock()
        check.run.return_value = {'cold': True}
        args = Namespace(weather_settle=0, offset=(0.,.4,4.), replication_timeout=1,
                         timeout=1, skip_projection=False, vertical_fov=66.5)
        targets = {'item': (10,80,10), 'set_block': (14,80,10)}
        captured = []

        def execute(client, code):
            compile(code, '<server-snippet>', 'exec')
            if code == probe.SETUP:
                return {'targets': targets}
            if "method=" in code:
                return {'returned': True, 'foreground': {'name': 'minecraft:decorated_pot'}}
            return {'accepted': True}

        def capture(check, target, offset, label, cold=False):
            captured.append(label)
            return {'capture': {}}

        def observe(check, code, timeout):
            compile(probe.CLIENT+code, '<client-snippet>', 'exec')
            return {'matched': code == probe.PROJECTION_STATUS, 'timed_out': True}

        with patch.object(probe, 'execute', side_effect=execute), \
                patch.object(probe, 'capture_stage', side_effect=capture), \
                patch.object(probe, 'observe', side_effect=observe), \
                patch.object(probe, 'analyze_body', return_value={'positive_control_passed': False}), \
                patch.object(probe, 'write_json'), patch.object(probe.time, 'sleep'):
            probe.run_probe(check, report, Path('unused.json'), args)

        self.assertEqual(['item_empty', 'set_block_empty', 'item_native_raw', 'set_block_native_raw',
                          'item_fixture_nbt', 'set_block_fixture_nbt',
                          'item_after_first_projection', 'set_block_after_first_projection'], captured)
        events = report['events']
        self.assertLess(events.index('set_block_native_raw_capture'), events.index('item_fixture_nbt'))
        self.assertLess(events.index('set_block_fixture_nbt_capture'), events.index('first_projection_requested'))
        self.assertTrue(report['completed'])
        self.assertFalse(report['passed'])
        for row in report['controls'].values():
            self.assertFalse(row['nbt_replication']['matched'])
            self.assertIn('after_first_projection', row['stages'])

    def test_cleanup_continues_after_independent_failure(self):
        check = Mock()
        check.run.side_effect = [RuntimeError('projection unavailable'), True]
        report = {'passed': True}
        with patch.object(probe, 'execute', return_value={'restored': True}) as execute:
            probe.cleanup(check, report)
        self.assertEqual(2, execute.call_count)
        self.assertIn('world', report['cleanup'])
        self.assertIn('environment', report['cleanup'])
        self.assertFalse(report['restored'])
        self.assertFalse(report['passed'])
        self.assertEqual(1, len(report['cleanup_errors']))


if __name__ == '__main__':
    unittest.main()
