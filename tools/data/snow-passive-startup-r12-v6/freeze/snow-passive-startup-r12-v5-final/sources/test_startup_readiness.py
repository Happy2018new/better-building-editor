"""Readiness reuses verified discovery while preserving deadline and ownership failures."""
from contextlib import ExitStack, nullcontext
import ctypes
from pathlib import Path
import socket
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances
import mcdk


class Clock:
    def __init__(self):
        self.value = 0

    def monotonic(self):
        return self.value

    def sleep(self, duration):
        self.value += duration


class StartupReadinessTests(unittest.TestCase):
    def launch(self, execute=None, discover=None, listeners=None, wait=3):
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            folder = Path(temporary)
            clock = Clock()
            identities = {101: 'mcdk-creation', 202: 'game-creation'}
            state = {'calls': [], 'opens': 0, 'clock': clock, 'identities': identities}
            process = SimpleNamespace(pid=101, poll=lambda: None)
            args = SimpleNamespace(project=str(folder), mcdk='mcdk.exe', game_exe='game.exe',
                owner='readiness-test', name='readiness-test', port=None, preset=None, wait=wait)
            snapshot = {'hwnd': 1, 'pid': 99, 'identity': 'editor', 'process': 'editor.exe'}
            guard = {'background_safe': True, 'window_noactivate': True, 'windows': [{'hwnd': 2}]}

            def discovery(pid, port, timeout):
                self.assertEqual(101, pid)
                if discover:
                    return discover(state, pid, port, timeout)
                clock.value += .5
                return {'children': [202], 'listeners': [101]}

            class Client:
                readiness_method = None

                def __init__(self, data, deadline):
                    self.data, self.deadline = data, deadline

                def __enter__(self):
                    state['opens'] += 1
                    return self

                def __exit__(self, *args):
                    pass

                def call(self, name, arguments):
                    self.readiness_method = 'tools/call'
                    state['calls'].append(arguments)
                    if execute:
                        result = execute(state, self.data, arguments)
                        if result is not None:
                            return result
                    result = ({'pid': 202, 'appdata': self.data['appdata']}
                              if 'import os' in arguments['code'] else self.data['token'])
                    return {'structuredContent': {'return_value': result}}

            def owners(port):
                return listeners(state, port) if listeners else [101]

            replacements = {
                'resolve_mcdk': Mock(return_value='mcdk.exe'), 'resolve_game': Mock(return_value='game.exe'),
                'registry_dir': Mock(return_value=folder / 'registry'),
                'file_lock': Mock(side_effect=lambda *args: nullcontext()),
                'prepare_config': Mock(return_value={'included_mod_dirs': [], 'world_folder_name': 'test-world',
                                                     'game_executable_path': 'game.exe'}),
                'prepare_world': Mock(return_value=(folder, folder)),
                'foreground_snapshot': Mock(return_value=snapshot),
                'validate_foreground_snapshot': Mock(return_value=True),
                'noactivate_contract': Mock(return_value={'requested': True, 'dll': {'path': 'guard.dll'},
                                                          'mcdk': {'path': 'mcdk.exe'}}),
                'background_guard_state': Mock(return_value=guard),
                'process_identity': Mock(side_effect=identities.get),
                'terminate_owned': Mock(), 'discover': Mock(side_effect=discovery),
                'listener_owners': Mock(side_effect=owners), 'ReadinessClient': Client,
            }
            for name, value in replacements.items():
                stack.enter_context(patch.object(instances, name, value))
            stack.enter_context(patch.object(instances.subprocess, 'Popen', return_value=process))
            stack.enter_context(patch.object(instances.time, 'monotonic', side_effect=clock.monotonic))
            stack.enter_context(patch.object(instances.time, 'sleep', side_effect=clock.sleep))
            result = instances.start(args)
            state.update(discovery_calls=replacements['discover'].call_count,
                         terminated=replacements['terminate_owned'].call_args_list)
            return result, state

    def test_late_ipc_reuses_one_discovery_then_checks_both_runtime_markers(self):
        def execute(state, data, arguments):
            if state['clock'].value < 1.5:
                raise mcdk.MCDKError('No IPC client connected')
        result, state = self.launch(execute=execute)
        self.assertTrue(result['ready'])
        self.assertEqual(1, state['discovery_calls'])
        self.assertEqual(3, state['opens'])
        self.assertEqual([True, True, False], [row['is_client'] for row in state['calls'][-3:]])
        self.assertEqual('No IPC client connected', result['last_sdk_error']['error'])
        self.assertEqual([], state['terminated'])

    def test_failed_sdk_raw_error_survives_deadline_without_another_cim_query(self):
        raw = {'code': -32001, 'message': 'IPC unavailable', 'data': {'target': 'client', 'detail': 'full raw'}}
        def execute(state, data, arguments):
            state['clock'].value += .6
            raise mcdk.RPCError(raw)
        result, state = self.launch(execute=execute, wait=2)
        self.assertFalse(result['ready'])
        self.assertTrue(result['readiness_deadline_reached'])
        self.assertEqual(raw, result['last_sdk_error']['raw_error'])
        self.assertEqual('client_process_environment', result['last_sdk_error']['phase'])
        self.assertEqual(result['last_sdk_error']['error'], result['error'])
        self.assertEqual(1, state['discovery_calls'])

    def test_game_pid_reuse_stops_sdk_retries_without_terminating_the_reused_process(self):
        def execute(state, data, arguments):
            state['identities'][202] = 'reused-game'
            raise mcdk.MCDKError('previous native failure')
        result, state = self.launch(execute=execute)
        self.assertFalse(result['ready'])
        self.assertIn('creation identity changed', result['error'])
        self.assertEqual(1, len(state['calls']))
        self.assertEqual(1, state['discovery_calls'])
        self.assertEqual([], state['terminated'])
        self.assertEqual('previous native failure', result['last_sdk_error']['error'])

    def test_loopback_listener_takeover_blocks_further_sdk_requests(self):
        def execute(state, data, arguments):
            raise mcdk.MCDKError('previous native failure')
        result, state = self.launch(execute=execute,
            listeners=lambda state, port: [999] if state['calls'] else [101])
        self.assertFalse(result['ready'])
        self.assertIn('another process', result['error'])
        self.assertEqual(1, len(state['calls']))
        self.assertEqual(1, state['discovery_calls'])
        self.assertEqual([], state['terminated'])

    def test_missing_listener_retries_only_same_identity_and_retains_the_discovery(self):
        def listeners(state, port):
            return [] if state['clock'].value < 1 else [101]
        result, state = self.launch(listeners=listeners)
        self.assertTrue(result['ready'])
        self.assertEqual(1, state['discovery_calls'])
        self.assertEqual(3, len(state['calls']))

    def test_mcdk_reuse_during_initial_discovery_cannot_bind_a_game(self):
        def discover(state, pid, port, timeout):
            state['identities'][101] = 'reused-mcdk'
            return {'children': [202], 'listeners': [101]}
        result, state = self.launch(discover=discover)
        self.assertFalse(result['ready'])
        self.assertIn('changed during discovery', result['error'])
        self.assertNotIn('game_pid', result)
        self.assertEqual([], state['calls'])
        self.assertEqual([], state['terminated'])

    def test_identity_change_during_listener_read_blocks_sdk_initialization(self):
        def listeners(state, port):
            state['identities'][202] = 'reused-game'
            return [101]
        result, state = self.launch(listeners=listeners)
        self.assertFalse(result['ready'])
        self.assertIn('changed during listener check', result['error'])
        self.assertEqual([], state['calls'])
        self.assertEqual([], state['terminated'])

    def test_initial_discovery_timeout_keeps_raw_error_and_output_with_bounded_budget(self):
        def discover(state, pid, port, timeout):
            self.assertEqual(1, timeout)
            state['clock'].value += timeout
            raise subprocess.TimeoutExpired(['owned discovery'], timeout, output=b'partial\r\n', stderr=b'err\r\n')
        result, state = self.launch(discover=discover, wait=1)
        self.assertFalse(result['ready'])
        self.assertEqual('TimeoutExpired', result['last_discovery_error']['error_type'])
        self.assertEqual('partial\r\n', result['discovery_timeouts'][0]['stdout'])
        self.assertEqual('err\r\n', result['discovery_timeouts'][0]['stderr'])
        self.assertEqual([], state['calls'])


class ReadinessNetworkDeadlineTests(unittest.TestCase):
    def test_actual_sdk_post_uses_remaining_timeout_and_never_sends_after_deadline(self):
        clock = Clock()
        clock.value = .75
        data = {'mcp_url': 'http://127.0.0.1:12345/mcp'}
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock()
        response.read.return_value = b'{"jsonrpc":"2.0","id":1,"result":{"ok":true}}'
        with patch.object(instances, 'verify_startup_endpoint'), \
             patch.object(instances.time, 'monotonic', side_effect=clock.monotonic):
            client = instances.ReadinessClient(data, 1)
            client.opener = Mock()
            client.opener.open.return_value = response
            self.assertEqual({'ok': True}, client.call('execute_code', {'code': '_result=1'}))
            self.assertEqual(.25, client.opener.open.call_args.kwargs['timeout'])
            clock.value = 1
            with self.assertRaisesRegex(TimeoutError, 'before tools/call'):
                client.call('execute_code', {'code': '_result=1'})
            self.assertEqual(1, client.opener.open.call_count)

    def test_automatic_initialize_calls_each_use_remaining_budget_and_reject_a_late_response(self):
        clock, observed = Clock(), []
        data = {'mcp_url': 'http://127.0.0.1:12345/mcp'}
        def post(client, method, params=None, notification=False):
            observed.append((method, client.timeout))
            clock.value += .4
            if method == 'initialize':
                client.session = 'test-session'
            return {}
        with patch.object(instances, 'verify_startup_endpoint'), \
             patch.object(instances.time, 'monotonic', side_effect=clock.monotonic), \
             patch.object(instances.Client, '_post', autospec=True, side_effect=post):
            client = instances.ReadinessClient(data, 1)
            with self.assertRaisesRegex(TimeoutError, 'after deadline'):
                client.__enter__()
        self.assertEqual(['initialize', 'notifications/initialized', 'tools/list'], [row[0] for row in observed])
        for actual, expected in zip([row[1] for row in observed], (1, .6, .2)):
            self.assertAlmostEqual(expected, actual)
        self.assertIsNone(client.session)

    def test_deadline_before_request_and_during_close_send_no_network_traffic(self):
        clock = Clock()
        data = {'mcp_url': 'http://127.0.0.1:12345/mcp'}
        with patch.object(instances, 'verify_startup_endpoint') as verify, \
             patch.object(instances.time, 'monotonic', side_effect=clock.monotonic), \
             patch.object(instances.Client, '_post') as post:
            client = instances.ReadinessClient(data, 1)
            clock.value = 1
            with self.assertRaisesRegex(TimeoutError, 'before tools/call'):
                client._post('tools/call')
            post.assert_not_called()
            client.session = 'test-session'
            clock.value = .9
            verify.side_effect = lambda data: setattr(clock, 'value', 1.1)
            client.opener = Mock()
            client.close()
            client.opener.open.assert_not_called()
            self.assertIsNone(client.session)


class ListenerTableTests(unittest.TestCase):
    def test_ipv4_listener_decoder_accepts_only_loopback_or_wildcard_for_the_requested_port(self):
        def row(state, address, port, pid):
            return struct.pack('<6I', state, int.from_bytes(socket.inet_aton(address), 'little'),
                               socket.htons(port), 0, 0, pid)
        rows = [row(2, '127.0.0.1', 12345, 101), row(2, '0.0.0.0', 12345, 101),
                row(5, '127.0.0.1', 12345, 202), row(2, '192.0.2.1', 12345, 999),
                row(2, '127.0.0.1', 54321, 999)]
        raw = struct.pack('<I', len(rows)) + b''.join(rows)
        self.assertEqual([101], instances.tcp_listener_owners(raw, 12345))
        with self.assertRaisesRegex(ValueError, 'Truncated'):
            instances.tcp_listener_owners(raw[:-1], 12345)

    def test_native_table_query_uses_ipv4_listener_class_only(self):
        raw = struct.pack('<I6I', 1, 2, 0x0100007f, socket.htons(12345), 0, 0, 101)
        calls = []
        def query(buffer, size, ordered, family, table_class, reserved):
            calls.append((family, table_class))
            size._obj.value = len(raw)
            if buffer is None:
                return 122
            ctypes.memmove(buffer, raw, len(raw))
            return 0
        function = Mock(side_effect=query)
        with patch.object(instances.ctypes, 'WinDLL', return_value=SimpleNamespace(GetExtendedTcpTable=function)):
            self.assertEqual([101], instances.listener_owners(12345))
        self.assertEqual([(socket.AF_INET, 3), (socket.AF_INET, 3)], calls)


if __name__ == '__main__':
    unittest.main()
