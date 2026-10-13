"""Risk-focused h0 budget, first-capture, handle-stop and replication regressions."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from test_owned_startup_supervisor import FakeHost
import supervise_snow_h0 as control
import verify_snow_h0_phase as phase_module
from verify_snow_h0_phase import camera_matches, palette_matches


class H0Host(FakeHost):
    def __init__(self, root):
        super().__init__(root)
        self.ready_at = 90
        self.launch_done_at = 90
        self.handle_counts = [100, 100, 100, 100, 100, 100, 100]
        self.handle_reads = 0
        self.ready_capture_fail = False

    def find_session(self, plan, initial):
        self.ready = self.clock >= self.ready_at
        self.session['ready'] = self.ready
        return super().find_session(plan, initial)

    def observe(self, session, plan, output, timeout):
        self.observations.append(output.name)
        self.clock += min(1, timeout)
        ready = output.name == 'startup-first-ready.png'
        value = {'ok': ready and not self.ready_capture_fail, 'reliable': ready and not self.ready_capture_fail,
                 'state_before': 'ready' if ready else 'starting', 'state_after': 'ready' if ready else 'starting',
                 'tcp': {'owned_established_pair_observed': ready}, 'pixels': {'width': 1994, 'height': 1105}}
        return {'returncode': 0 if value['ok'] else 1, 'stdout': json.dumps(value), 'timeout': False}

    def handle_sample(self, session):
        count = self.handle_counts[min(self.handle_reads, len(self.handle_counts) - 1)]
        self.handle_reads += 1
        return {'game': {'status': 'live', 'handle_count': count}, 'mcdk': {'status': 'live', 'handle_count': 200}}


class FiniteControlTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        patch = mock.patch.object(control, 'ROOT', self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.host = H0Host(self.root)
        self.plan = {'project': str(self.root), 'owner': self.host.session['owner'], 'name': self.host.session['name'],
                     'protected_processes': {'game': {'pid': 777}, 'mcdk': {'pid': 888}},
                     'budgets': {'total': 240, 'work': 190, 'cleanup_reserved': 50, 'launcher_wait': 90}}
        self.phase_calls = []

    def phase(self, plan, host, session, output, work_deadline, restore_deadline, health):
        self.phase_calls.append({'remaining': work_deadline - host.now(), 'restore_deadline': restore_deadline})
        for unused in range(4):
            host.clock += 20
            health()
        return {'completed': True, 'cleanup_errors': []}

    def run_control(self):
        return control.supervise(self.plan, self.host, self.root / 'run', self.phase)

    def test_ready_world_frame_starts_one_matrix_with_reserved_budget_and_owned_cleanup(self):
        value = self.run_control()
        self.assertTrue(value['diagnostic_completed'])
        self.assertEqual(1, value['launches'])
        self.assertEqual(1, len(self.phase_calls))
        self.assertGreaterEqual(self.phase_calls[0]['remaining'], 83)
        self.assertEqual(210, self.phase_calls[0]['restore_deadline'])
        self.assertLessEqual(value['run_elapsed_seconds'], 240)
        self.assertEqual(['startup-first-scheduled.png', 'startup-first-ready.png'], self.host.observations)
        self.assertTrue(value['owned_processes_dead'])
        self.assertTrue(self.host.restored)
        self.assertEqual({11, 22}, {row['pid'] for row in self.host.force_stops})

    def test_first_ready_capture_failure_is_never_replaced_or_relaunched(self):
        self.host.ready_capture_fail = True
        value = self.run_control()
        self.assertFalse(value['matrix_started'])
        self.assertEqual([], self.phase_calls)
        self.assertEqual(1, self.host.observations.count('startup-first-ready.png'))
        self.assertEqual(1, self.host.launches)
        self.assertTrue(value['owned_processes_dead'])

    def test_late_ready_refuses_matrix_even_when_world_frame_is_valid(self):
        self.host.ready_at = self.host.launch_done_at = 112
        value = self.run_control()
        self.assertIn('less than 83', value['error'])
        self.assertFalse(value['matrix_started'])
        self.assertEqual([], self.phase_calls)
        self.assertTrue(value['owned_processes_dead'])

    def test_two_post_ready_rapid_intervals_stop_only_own_processes(self):
        self.host.handle_counts = [100] * 7 + [10100, 20100]
        value = self.run_control()
        self.assertTrue(value['handle_rule_triggered'])
        self.assertEqual('persistent_post_ready_growth', value['handle_stop_reason'])
        self.assertTrue(value['matrix_started'])
        self.assertEqual(1, len(self.phase_calls))
        self.assertEqual({11, 22}, {row['pid'] for row in self.host.force_stops})
        self.assertTrue(value['owned_processes_dead'])

    def test_one_rapid_interval_does_not_establish_persistent_growth(self):
        self.host.handle_counts = [100] * 7 + [10100, 10500, 11000, 11200]
        value = self.run_control()
        self.assertFalse(value['handle_rule_triggered'])
        self.assertTrue(value['diagnostic_completed'])
        self.assertFalse(value['resource_health_accepted'])

    def test_pre_ready_growth_is_observation_only_and_ready_starts_a_new_baseline(self):
        self.host.handle_counts = [100, 10100, 20100, 30100, 40100, 50100, 60100, 60100]
        value = self.run_control()
        self.assertTrue(value['diagnostic_completed'])
        self.assertFalse(value['handle_rule_triggered'])
        pre_ready = [row for row in value['handle_samples'] if not row['ready']]
        self.assertGreaterEqual(len(pre_ready), 3)
        self.assertTrue(all(row['processes']['game']['pre_ready_growth_observation_only'] for row in pre_ready))
        self.assertTrue(all(row['processes']['game']['consecutive_qualifying_intervals'] == 0 for row in pre_ready))
        baseline = next(row for row in value['handle_samples'] if row['ready'])
        self.assertTrue(baseline['post_ready_baseline'])
        self.assertFalse(baseline['processes']['game']['qualifying_interval'])

    def test_absolute_game_limit_stops_even_during_pre_ready_loading(self):
        self.host.handle_counts = [100000]
        value = self.run_control()
        self.assertTrue(value['handle_rule_triggered'])
        self.assertEqual('absolute_game_handles_at_least_100000', value['handle_stop_reason'])
        self.assertFalse(value['matrix_started'])
        self.assertTrue(value['owned_processes_dead'])

    def test_capacity_exhaustion_does_not_launch_and_still_restores(self):
        self.host.pids.append(105)
        value = self.run_control()
        self.assertEqual(0, self.host.launches)
        self.assertTrue(self.host.restored)
        self.assertFalse(value['diagnostic_completed'])

    def test_reused_owned_creation_refuses_matrix_and_cleanup_of_new_identity(self):
        self.host.fault = 'reused'
        value = self.run_control()
        self.assertIn('binding changed', value['error'])
        self.assertFalse(value['matrix_started'])
        self.assertEqual([], self.phase_calls)


class StateContractTests(unittest.TestCase):
    def test_normal_stop_uses_actual_h0_owner_and_parent_timeout(self):
        host = object.__new__(control.WindowsHost)
        for owner in ('snow-r12-h0-native', 'snow-r12-h0-alpha'):
            with self.subTest(owner=owner), mock.patch.object(control.subprocess, 'run',
                    return_value=SimpleNamespace(returncode=0, stdout='stopped', stderr='')) as call:
                value = host.normal_stop({'session_file': 'owned-session.json', 'owner': owner}, 4.25)
                command = call.call_args.args[0]
                self.assertEqual(owner, command[command.index('--owner') + 1])
                self.assertEqual(4.25, call.call_args.kwargs['timeout'])
                self.assertEqual(0, value['returncode'])

    def test_replication_requires_exact_h0_and_covered_extra_poppy(self):
        self.assertTrue(palette_matches({'common': [['minecraft:snow_layer', 8, [0]]],
                                         'extra': [['minecraft:poppy', 0, [0]]]}, 'covered'))
        self.assertFalse(palette_matches({'common': [['minecraft:snow_layer', 15, [0]]],
                                          'extra': [['minecraft:poppy', 0, [0]]]}, 'covered'))
        self.assertFalse(palette_matches({'common': [['minecraft:snow_layer', 8, [0]]], 'extra': []}, 'covered'))
        self.assertFalse(palette_matches({'common': [['minecraft:snow_layer', 0, [0]]],
                                          'extra': [['minecraft:poppy', 0, [0]]]}, 'snow'))
        self.assertTrue(palette_matches({'common': [], 'extra': []}, 'blank'))

    def test_camera_and_player_drift_are_failures_without_normalization(self):
        expected = {'position': [4.5, 117.65, 4.], 'rotation': [0., 90., 0.]}
        actual = copy.deepcopy(expected)
        actual['player'] = [0., -60., 0.]
        self.assertTrue(camera_matches(actual, expected, [0., -60., 0.]))
        actual['player'][1] += 1
        self.assertFalse(camera_matches(actual, expected, [0., -60., 0.]))

    def test_frozen_snippets_and_generated_cleanup_are_syntax_valid(self):
        root = Path(__file__).resolve().parents[1]
        snow = phase_module.constants(root / 'tools/verify_snow_plant_visibility.py',
                   ('LOAD', 'NATIVE_SETUP', 'NATIVE_MUTATE', 'NATIVE_SNOW', 'NATIVE_CLEANUP'))
        for code in (snow['LOAD'] % ('poppy', 0, 'covered'), snow['NATIVE_SETUP'] % ((6, 117, 6),),
                     snow['NATIVE_MUTATE'] % ('poppy', 'covered', 0), snow['NATIVE_SNOW'] % 1,
                     phase_module.CAMERA_SET, phase_module.SERVER_PREFLIGHT,
                     'import json,sys\nif hasattr(sys,"_snow_visibility_native"):\n' +
                     '\n'.join(' ' + line for line in snow['NATIVE_CLEANUP'].splitlines()) +
                     '\nelse:_result=json.dumps([])\n'):
            compile(code, '<frozen-snow-snippet>', 'exec')

    def test_resource_stop_after_partial_setup_still_attempts_both_sdk_restorations(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            stub = output / 'empty-client.py'
            stub.write_text('pass\n', encoding='ascii')
            plan = {'texture_condition': 'native_original', 'files': {
                'mcdk_client': {'path': str(stub)},
                'snow_reference': {'path': str(root / 'tools/verify_snow_plant_visibility.py')},
                'blueprint_reference': {'path': str(root / 'tools/verify_debug_blueprints.py')},
                'visual_reference': {'path': str(root / 'tools/verify_debug_visuals.py')}}}
            state = {'stopped': False, 'calls': [], 'cleanup': []}
            preflight = {'player_foot': [0., -60., 0.], 'player_flying': False}
            host = SimpleNamespace(now=lambda: 100.)

            class FakeClient:
                def __init__(self, timeout):
                    self.timeout = timeout

                def _post(self, method, arguments):
                    code = arguments['code']
                    state['calls'].append(code)
                    if code.startswith('import json,sys\nif hasattr(sys,'):
                        state['cleanup'].append('native')
                        return []
                    if 'cam.ResetCameraPos()' in code:
                        state['cleanup'].append('client')
                        return {'position': [0., -58., 0.], 'rotation': [0., 0., 0.],
                                'pitch_lock': False, 'yaw_lock': False, 'fov': 70., 'player': [0., -60., 0.]}
                    if "sys._blueprint_visual_saved['fov']" in code:
                        return {'camera_pos': [0., -58., 0.], 'camera_rot': [0., 0., 0.],
                                'pitch_lock': False, 'yaw_lock': False, 'fov': 70., 'player': [0., -60., 0.]}
                    if 'players=server_api.GetPlayerList()' in code:
                        return preflight
                    if 'position=(4.5,117.65,4.)' in code:
                        state['stopped'] = True
                        return {'position': [4.5, 117.65, 4.], 'rotation': [0., 90., 0.]}
                    return True

                def call(self, name, arguments):
                    return self._post(name, arguments)

                def __enter__(self):
                    return self

                def close(self):
                    pass

            def make_module(name):
                return SimpleNamespace(Client=FakeClient, return_value=lambda value: value)

            def health():
                if state['stopped']:
                    raise RuntimeError('persistent rapid growth')

            with mock.patch.object(phase_module, 'ModuleType', side_effect=make_module):
                value = phase_module.run_phase(plan, host, {'id': 'owned', 'session_file': 'owned.json',
                    'owner': 'owned', 'mcp_url': 'http://owned'}, output, 190., 210., health)
            self.assertFalse(value['completed'])
            self.assertIn('persistent rapid growth', value['error'])
            self.assertEqual(['native', 'client'], state['cleanup'])
            self.assertEqual([], value['cleanup_errors'])


if __name__ == '__main__':
    unittest.main()
