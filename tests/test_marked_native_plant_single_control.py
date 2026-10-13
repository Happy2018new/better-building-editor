"""Check the minimal diagnostic's scope and fresh runtime identity controls."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import verify_marked_native_plant as observer


class SingleNativePlantControlTests(unittest.TestCase):
    def args(self, **values):
        defaults = dict(single_positive_control=True, partition='calibration', stage='alpha_marker')
        defaults.update(values)
        return SimpleNamespace(**defaults)

    def test_single_control_uses_one_predeclared_cell_and_public_view(self):
        plan = {'calibration_coordinates': [[-47, 117, -70], [6, 117, 6], [7, 117, 6], [6, 117, 7]]}
        coordinates, views = observer.observation_scope(self.args(), plan)
        self.assertEqual([[6, 117, 6]], coordinates)
        self.assertEqual({'public': (-2., .15, -2.5)}, views)

    def test_single_control_cannot_open_holdouts_opaque_stage_or_an_undeclared_cell(self):
        plan = {'calibration_coordinates': [[6, 117, 6]]}
        for changes in ({'partition': 'holdout'}, {'stage': 'opaque_marker'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                observer.observation_scope(self.args(**changes), plan)
        with self.assertRaises(ValueError):
            observer.observation_scope(self.args(), {'calibration_coordinates': [[7, 117, 6]]})

    def probe(self, change=None):
        session = {'game_pid': 123, 'token': 'owned-token'}
        calls = []

        class Client:
            def call(self, name, arguments):
                index = len(calls)
                nonce = 'fresh-%d' % index
                calls.append((name, arguments))
                if repr(nonce) not in arguments['code']:
                    raise AssertionError('Fresh nonce was not included in the requested game code')
                value = {'nonce': nonce, 'pid': 123, 'token': 'owned-token', 'clock': 10. + index}
                if change:
                    change(index, value)
                return {'structuredContent': {'return_value': json.dumps(value)}}

        receipt = {}
        with patch.object(observer.uuid, 'uuid4', side_effect=[SimpleNamespace(hex='fresh-%d' % i)
                                                              for i in range(4)]), \
                patch.object(observer.time, 'sleep'):
            observer.runtime_control(Client(), session, receipt)
        return calls, receipt

    def test_fresh_client_and_server_rounds_prove_only_runtime_progress(self):
        calls, receipt = self.probe()
        self.assertEqual([True, False, True, False], [args['is_client'] for _, args in calls])
        self.assertTrue(all(name == 'execute_code' and args['direct_return'] for name, args in calls))
        self.assertIs(True, receipt['verified'])
        self.assertIs(False, receipt['render_progress_verified'])
        self.assertEqual(4, len(receipt['samples']))

    def test_stale_nonce_wrong_process_or_wrong_session_is_rejected(self):
        for field, wrong in (('nonce', 'stale'), ('pid', 456), ('token', 'other-owner')):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'stale or misrouted'):
                self.probe(lambda index, value: value.update({field: wrong}) if index == 1 else None)

    def test_frozen_or_nonfinite_runtime_clock_is_rejected(self):
        for clock in (10., float('nan'), None):
            with self.subTest(clock=clock), self.assertRaisesRegex(ValueError, 'clock'):
                self.probe(lambda index, value: value.update(clock=clock) if index == 2 else None)


if __name__ == '__main__':
    unittest.main()
