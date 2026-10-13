"""Exercise startup ownership and capture gates with a fake host only."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import observe_owned_startup as observer


class FakeHost:
    def __init__(self, session):
        self.session = session
        self.processes = {session[kind + '_pid']: {'identity': session[kind + '_identity'],
            'executable': session['game_executable'] if kind == 'game'
            else session['noactivation']['mcdk']['path']} for kind in ('mcdk', 'game')}
        self.guard_value = {'background_safe': True, 'window_noactivate': True,
            'foreground': {'pid': 999, 'hwnd': 500}, 'windows': [
                {'hwnd': 600, 'pid': session['game_pid'], 'process': 'Minecraft.Windows.exe',
                 'width': 640, 'height': 360, 'noactivate': True, 'minimized': False}]}
        self.capture_calls = []
        self.inspect_calls = []
        self.rows = []
        self.on_capture = None
        self.blank = False
        self.frame_qpc = 101

    def inspect_process(self, pid):
        self.inspect_calls.append(pid)
        return self.processes.get(pid)

    def guard(self, _):
        return copy.deepcopy(self.guard_value)

    def tcp_rows(self):
        return self.rows

    def capture(self, command, timeout):
        self.capture_calls.append((command, timeout))
        image = Image.new('RGB', (640, 360), 'black')
        if not self.blank:
            image.paste('white', (0, 0, 320, 360))
        image.save(command[-1])
        if self.on_capture:
            self.on_capture()
        frame = {'ok': True, 'backend': 'Windows.Graphics.Capture', 'native_resolution': True,
                 'request_qpc_100ns': 100, 'frame_qpc_100ns': self.frame_qpc,
                 'width': 640, 'height': 360}
        return SimpleNamespace(returncode=0, stdout=json.dumps(frame), stderr='')


class OwnedStartupObserverTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.helper = self.root / 'single-wgc.exe'
        self.helper.write_bytes(b'Offline fake helper; never executed')
        self.session_file = self.root / 'session.json'
        self.session = {'schema': 1, 'id': 'owned-session', 'owner': 'snow-r11-position',
            'project': str(self.root), 'session_file': str(self.session_file), 'state': 'starting',
            'log': str(self.root / 'mcdk.log'), 'game_pid': 11, 'game_identity': '11111',
            'mcdk_pid': 22, 'mcdk_identity': '22222',
            'game_executable': str(self.root / 'Minecraft.Windows.exe'),
            'noactivation': {'requested': True, 'mcdk': {'path': str(self.root / 'mcdk.exe')}}}
        self.write_session()
        (self.root / 'mcdk.log').write_bytes(b'[MCDK] MCP Server 127.0.0.1:52112\n'
            b'[MCDK] IPC Bridge listening on port 52115\n')
        self.host = FakeHost(self.session)
        self.addCleanup(mock.patch.stopall)
        mock.patch.object(observer, 'CAPTURE_EXECUTABLE', self.helper).start()
        mock.patch.object(observer, 'CAPTURE_SHA256', hashlib.sha256(self.helper.read_bytes()).hexdigest()).start()
        mock.patch.object(observer, 'WindowsHost', side_effect=AssertionError('No OS access in unit tests')).start()

    def write_session(self):
        self.session_file.write_text(json.dumps(self.session), encoding='utf8')

    def observe(self, name='snapshot', **kwargs):
        options = {'session_file': self.session_file, 'owner': self.session['owner'],
                   'project': self.root, 'output': self.root / (name + '.png'),
                   'executable': self.helper, 'host': self.host}
        options.update(kwargs)
        result = observer.observe(**options)
        receipt = json.loads(options['output'].with_suffix('.startup.json').read_bytes())
        self.assertEqual(result, receipt)
        return result

    def assert_refused(self, expected, **kwargs):
        result = self.observe(**kwargs)
        self.assertIs(False, result['ok'])
        self.assertIs(False, result['reliable'])
        self.assertIn(expected, result['error'])
        self.assertEqual([], self.host.capture_calls)
        return result

    def test_starting_and_failed_live_states_are_observable_without_readiness(self):
        for state in ('starting', 'failed', 'ready'):
            with self.subTest(state=state):
                self.session['state'] = state
                self.write_session()
                result = self.observe(name=state)
                self.assertIs(True, result['ok'])
                self.assertEqual(state, result['state_before'])
                self.assertEqual(state, result['state_after'])
                self.assertEqual(52115, result['ipc_port']['port'])
                self.assertIs(False, result['ipc_port']['actual_child_environment_recorded'])
                self.assertIs(False, result['production_acceptance'])
                self.assertIs(False, result['sdk_or_mcp_called'])
                self.assertIs(False, result['game_or_mcdk_launched'])
                self.assertIs(False, result['game_input_or_window_mutation_attempted'])
        command, timeout = self.host.capture_calls[0]
        self.assertEqual([str(self.helper.resolve()), '600', '11', '11111'], command[:4])
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 15)

    def test_wrong_owner_fails_before_host_access(self):
        self.assert_refused('owner mismatch', owner='another-owner')
        self.assertEqual([], self.host.inspect_calls)

    def test_wrong_project_fails_before_host_access(self):
        other = self.root / 'other-project'
        other.mkdir()
        self.assert_refused('project mismatch', project=other)
        self.assertEqual([], self.host.inspect_calls)

    def test_stopped_state_cannot_be_observed(self):
        self.session['state'] = 'stopped'
        self.write_session()
        self.assert_refused('does not permit state')

    def test_noactivation_request_is_required(self):
        self.session['noactivation']['requested'] = False
        self.write_session()
        self.assert_refused('did not request')

    def test_dead_process_is_refused(self):
        self.host.processes[11] = None
        self.assert_refused('dead or unavailable: game')

    def test_pid_reuse_is_refused_for_each_owned_process(self):
        for pid in (11, 22):
            with self.subTest(pid=pid):
                self.host = FakeHost(self.session)
                self.host.processes[pid]['identity'] = 'reused'
                self.assert_refused('creation identity changed', name='reused-' + str(pid))

    def test_same_basename_at_another_executable_path_is_refused(self):
        self.host.processes[11]['executable'] = str(self.root / 'other/Minecraft.Windows.exe')
        self.assert_refused('executable changed: game')

    def test_unapproved_helper_path_or_bytes_are_refused(self):
        other = self.root / 'other-wgc.exe'
        other.write_bytes(self.helper.read_bytes())
        self.assert_refused('not the approved', executable=other)
        self.helper.write_bytes(b'Changed binary')
        self.assert_refused('not the approved', name='changed-helper')

    def test_foreground_game_is_refused_without_capture(self):
        self.host.guard_value['foreground']['pid'] = 11
        self.assert_refused('foreground')

    def test_minimized_game_is_refused_without_capture(self):
        self.host.guard_value['windows'][0]['minimized'] = True
        self.assert_refused('minimized')

    def test_small_or_unguarded_window_is_refused(self):
        self.host.guard_value['windows'][0]['width'] = 639
        self.assert_refused('dimensions are below')
        self.host.guard_value['windows'][0]['width'] = 640
        self.host.guard_value['windows'][0]['noactivate'] = False
        self.assert_refused('lost the noactivation', name='no-guard')

    def test_window_pid_changed_is_refused(self):
        self.host.guard_value['windows'][0]['pid'] = 33
        self.assert_refused('window ownership changed')

    def test_identity_reuse_during_capture_rejects_pixels(self):
        self.host.on_capture = lambda: self.host.processes[11].update(identity='reused')
        result = self.observe()
        self.assertIs(False, result['ok'])
        self.assertIn('creation identity changed', result['error'])
        self.assertEqual(1, len(self.host.capture_calls))

    def test_foreground_or_dimension_change_during_capture_rejects_pixels(self):
        for change, expected in (({'foreground': {'pid': 11}}, 'foreground'),
                                 ({'windows': [dict(self.host.guard_value['windows'][0], width=641)]},
                                  'dimensions changed')):
            with self.subTest(expected=expected):
                self.host = FakeHost(self.session)
                self.host.on_capture = lambda change=change: self.host.guard_value.update(change)
                result = self.observe(name=expected)
                self.assertIs(False, result['ok'])
                self.assertIn(expected, result['error'])
                self.assertEqual(1, len(self.host.capture_calls))

    def test_blank_or_stale_frame_is_retained_as_failed_evidence(self):
        self.host.blank = True
        result = self.observe(name='blank')
        self.assertIs(False, result['ok'])
        self.assertIn('image is blank', result['error'])
        self.assertTrue((self.root / 'blank.png').is_file())
        self.host.blank = False
        self.host.frame_qpc = 99
        result = self.observe(name='stale')
        self.assertIs(False, result['ok'])
        self.assertIn('fresh native', result['error'])
        self.assertEqual(2, len(self.host.capture_calls))

    def test_evidence_is_not_overwritten_or_mutation_replayed(self):
        self.observe()
        with self.assertRaisesRegex(ValueError, 'fresh output'):
            self.observe()
        self.assertEqual(1, len(self.host.capture_calls))

    def test_session_rebinding_during_capture_rejects_pixels(self):
        def rebind():
            self.session['noactivation']['mcdk']['path'] = str(self.root / 'another/mcdk.exe')
            self.write_session()
        self.host.on_capture = rebind
        result = self.observe()
        self.assertIs(False, result['ok'])
        self.assertIn('MCDK executable binding changed', result['error'])

    def test_capture_timeout_is_retained_without_retry(self):
        import subprocess
        self.host.capture = mock.Mock(side_effect=subprocess.TimeoutExpired('single-wgc', 15))
        result = self.observe()
        self.assertIs(False, result['ok'])
        self.assertIs(True, result['timeout'])
        self.assertIn('TimeoutExpired', result['error'])
        self.assertEqual(1, self.host.capture.call_count)

    def test_frame_dimension_mismatch_by_one_pixel_is_still_refused(self):
        capture = self.host.capture
        def wrong_size(command, timeout):
            result = capture(command, timeout)
            frame = json.loads(result.stdout)
            frame['width'] += 1
            return SimpleNamespace(returncode=0, stdout=json.dumps(frame), stderr='')
        self.host.capture = wrong_size
        result = self.observe()
        self.assertIs(False, result['ok'])
        self.assertIs(False, result['reliable'])
        self.assertIn('Captured dimensions differ', result['error'])
        self.assertEqual(1, len(self.host.capture_calls))

    def test_ambiguous_listener_log_is_refused_without_capture(self):
        (self.root / 'mcdk.log').write_bytes(b'[MCDK] IPC Bridge listening on port 52115\n'
            b'[MCDK] IPC Bridge listening on port 52116\n')
        self.assert_refused('ambiguous IPC listener ports')

    def test_missing_listener_log_remains_unknown(self):
        (self.root / 'mcdk.log').unlink()
        result = self.observe()
        self.assertIs(True, result['ok'])
        self.assertIsNone(result['ipc_port']['port'])
        self.assertIs(False, result['tcp']['owned_established_pair_observed'])

    def test_listener_port_is_not_assumed_from_mcp_port(self):
        result = self.observe()
        self.assertEqual(52115, result['ipc_port']['port'])
        self.assertIs(False, result['tcp']['owned_listener_observed'])
        self.assertIs(False, result['tcp']['owned_established_pair_observed'])

    def test_passive_tcp_pairs_both_owned_endpoints_and_ignores_other_clients(self):
        common = {'local_address': '127.0.0.1', 'remote_address': '127.0.0.1'}
        self.host.rows = [dict(common, pid=22, state=2, local_port=52115, remote_port=0),
                          dict(common, pid=11, state=5, local_port=55000, remote_port=52115),
                          dict(common, pid=22, state=5, local_port=52115, remote_port=55000),
                          dict(common, pid=33, state=5, local_port=55001, remote_port=52115)]
        result = self.observe()
        self.assertIs(True, result['tcp']['owned_listener_observed'])
        self.assertIs(True, result['tcp']['owned_established_pair_observed'])
        self.assertEqual(3, len(result['tcp']['ipv4_rows']))
        self.host.rows = self.host.rows[:2]
        result = self.observe(name='unpaired')
        self.assertIs(False, result['tcp']['owned_established_pair_observed'])
        self.assertIs(False, result['tcp']['private_ipc_connection_attempted'])

    def test_tcp_decoder_uses_network_order_and_rejects_truncation(self):
        address = int.from_bytes(bytes((127, 0, 0, 1)), 'little')
        port = int.from_bytes((52115).to_bytes(2, 'big') + b'\0\0', 'little')
        raw = struct.pack('<I6I', 1, 2, address, port, 0, 0, 22)
        self.assertEqual([{'state': 2, 'pid': 22, 'local_address': '127.0.0.1',
                           'local_port': 52115, 'remote_address': '0.0.0.0', 'remote_port': 0}],
                         observer.decode_tcp_table(raw))
        with self.assertRaisesRegex(ValueError, 'Truncated IPv4 TCP rows'):
            observer.decode_tcp_table(raw[:-1])


if __name__ == '__main__':
    unittest.main()
