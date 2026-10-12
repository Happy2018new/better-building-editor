"""Protected execute_code refuses unavailable windows before game-thread dispatch."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import mcdk


class Response:
    headers = {'Mcp-Session-Id': 'local-test-session'}

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode('ascii')


class ProtectedExecutePreflightTests(unittest.TestCase):
    def setUp(self):
        self.binding = {'schema': 1, 'id': 'assigned-instance', 'state': 'ready',
                        'session_file': str(ROOT / 'test-session.json'), 'owner': 'assigned-owner',
                        'game_pid': 123, 'game_identity': '456', 'mcdk_pid': 124, 'mcdk_identity': '457',
                        'mcp_url': 'http://127.0.0.1:1/mcp', 'token': 'owned-token',
                        'game_executable': 'Minecraft.Windows.exe',
                        'noactivation': {'requested': True, 'background_safe': True, 'window_noactivate': True}}
        self.window = {'hwnd': 42, 'pid': 123, 'process': 'Minecraft.Windows.exe',
                       'title': 'Owned Game', 'width': 800, 'height': 600, 'minimized': False,
                       'x': 10, 'y': 20, 'noactivate': True}
        self.guard = {'foreground': {'hwnd': 99, 'pid': 900}, 'windows': [self.window],
                      'background_safe': True, 'window_noactivate': True}
        self.load = self.patch('load_session', return_value=self.binding)
        self.observe = self.patch('background_guard_state', return_value=self.guard)
        self.opener = mock.Mock()
        self.patch('urllib.request.build_opener', return_value=self.opener)
        self.patch('os.environ', new={})
        self.requests = []
        self.opener.open.side_effect = self.reply

    def patch(self, target, **kwargs):
        patcher = mock.patch('mcdk.' + target, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    def reply(self, request, **kwargs):
        if request.get_method() == 'DELETE':
            return Response({})
        payload = json.loads(request.data)
        self.requests.append(payload)
        result = ({'structuredContent': {'return_value': 'owned-token'}}
                  if payload['method'] == 'tools/call' and payload['params']['name'] == 'execute_code'
                  else {'content': [{'type': 'text', 'text': 'logs'}]})
        return Response({'jsonrpc': '2.0', 'id': payload.get('id'), 'result': result})

    def client(self, **kwargs):
        return mcdk.Client(**kwargs)

    def assert_no_execute_dispatched(self):
        self.assertFalse(any(request['method'] == 'tools/call' and
                             request['params']['name'] == 'execute_code' for request in self.requests))

    def test_minimized_token_probe_fails_before_execute_in_client_enter(self):
        self.window['minimized'] = True
        client = self.client(timeout=60)
        with self.assertRaises(mcdk.ProtectedWindowError) as caught:
            client.__enter__()
        error = caught.exception.error
        self.assertEqual('owned_game_window_is_minimized', error['reason'])
        self.assertTrue(error['window_unavailable'])
        self.assertFalse(error['execute_code_dispatched'])
        self.assertFalse(error['python_return_checked'])
        self.assertEqual(error, client.last_execute_code_preflight)
        self.assertEqual(self.guard, error['window_guard'])
        self.assert_no_execute_dispatched()
        self.load.assert_any_call(self.binding['session_file'], self.binding['owner'], live=True)
        self.assertIsNone(client.session)

    def test_missing_or_zero_client_window_fails_before_business_execute(self):
        for windows in ([], [dict(self.window, width=0, height=0)]):
            with self.subTest(windows=windows):
                self.guard['windows'] = windows
                with self.assertRaises(mcdk.ProtectedWindowError) as caught:
                    self.client().call('execute_code', {'code': 'world_mutation()', 'is_client': False})
                self.assertTrue(caught.exception.error['window_unavailable'])
                self.assert_no_execute_dispatched()

    def test_healthy_protected_session_still_verifies_token_and_sends_business_code(self):
        with self.client() as client:
            result = client.call('execute_code', {'code': '_result = 1', 'is_client': False})
            self.assertEqual('owned-token', mcdk.return_value(result))
            self.assertTrue(client.last_execute_code_preflight['ok'])
            self.assertTrue(client.last_execute_code_preflight['execute_code_dispatched'])
        execute = [request for request in self.requests if request['method'] == 'tools/call']
        self.assertEqual(3, len(execute))
        self.assertEqual('_result = 1', execute[-1]['params']['arguments']['code'])
        self.assertEqual(3, self.observe.call_count)

    def test_unbound_log_and_execute_calls_do_not_observe_windows_or_load_sessions(self):
        client = self.client(bind_session=False)
        client.call('get_latest_logs', {})
        client.call('execute_code', {'code': '_result = 1'})
        self.observe.assert_not_called()
        self.load.assert_not_called()
        self.assertEqual(['get_latest_logs', 'execute_code'],
                         [request['params']['name'] for request in self.requests])

    def test_missing_or_inactive_protection_keeps_existing_bound_behavior(self):
        self.window['minimized'] = True
        for protection in (None, {}, {'requested': False}, {'requested': 1}):
            with self.subTest(protection=protection):
                self.binding['noactivation'] = protection
                self.client().call('execute_code', {'code': '_result = 1'})
        self.observe.assert_not_called()
        self.assertEqual(8, len(self.requests))

    def test_foreground_and_guard_loss_have_distinct_predispatch_errors(self):
        for fault, reason, flag in (('foreground', 'owned_game_is_foreground', 'owned_process_foreground'),
                                   ('style', 'owned_game_background_guard_invalid', 'guard_invalid'),
                                   ('contract', 'protected_session_contract_invalid', 'guard_invalid')):
            with self.subTest(fault=fault):
                guard = copy.deepcopy(self.guard)
                binding = copy.deepcopy(self.binding)
                if fault == 'foreground':
                    guard['foreground']['pid'] = 123
                elif fault == 'style':
                    guard['windows'][0]['noactivate'] = False
                else:
                    binding['noactivation']['window_noactivate'] = False
                with mock.patch.object(mcdk, 'load_session', return_value=binding), \
                        mock.patch.object(mcdk, 'background_guard_state', return_value=guard):
                    with self.assertRaises(mcdk.ProtectedWindowError) as caught:
                        self.client().call('execute_code', {'code': '_result = 1'})
                self.assertEqual(reason, caught.exception.error['reason'])
                self.assertTrue(caught.exception.error[flag])
                self.assert_no_execute_dispatched()

    def test_window_becoming_minimized_after_token_blocks_business_code(self):
        unavailable = copy.deepcopy(self.guard)
        unavailable['windows'][0]['minimized'] = True
        with mock.patch.object(mcdk, 'background_guard_state', side_effect=[self.guard, unavailable]):
            with self.assertRaises(mcdk.ProtectedWindowError):
                self.client().call('execute_code', {'code': 'world_mutation()'})
        self.assertEqual(1, len(self.requests))
        self.assertIn('_pyreact_mcdk_session', self.requests[0]['params']['arguments']['code'])

    def test_owner_loader_failure_and_changed_identity_are_not_sent_to_runtime(self):
        client = self.client()
        with mock.patch.object(mcdk, 'load_session', side_effect=ValueError('Instance owner mismatch')):
            with self.assertRaisesRegex(ValueError, 'owner mismatch'):
                client._post('tools/call', {'name': 'execute_code', 'arguments': {}})
        changed = dict(self.binding, game_identity='changed')
        with mock.patch.object(mcdk, 'load_session', return_value=changed):
            with self.assertRaisesRegex(mcdk.MCDKError, 'identity changed'):
                client._post('tools/call', {'name': 'execute_code', 'arguments': {}})
        self.observe.assert_not_called()
        self.assert_no_execute_dispatched()

    def test_unavailable_window_observation_retains_a_structured_error(self):
        self.observe.side_effect = OSError('window census failed')
        with self.assertRaises(mcdk.ProtectedWindowError) as caught:
            self.client().call('execute_code', {'code': '_result = 1'})
        self.assertTrue(caught.exception.error['window_unavailable'])
        self.assertEqual('OSError: window census failed', caught.exception.error['observation_error'])
        self.assert_no_execute_dispatched()

    def test_invalid_python_return_remains_a_different_error_after_healthy_preflight(self):
        client = self.client()
        self.opener.open.return_value = Response({'id': 1, 'result': {'content': []}})
        self.opener.open.side_effect = None
        with self.assertRaisesRegex(mcdk.MCDKError, 'execute_code returned no value') as caught:
            client.call('execute_code', {'code': '_result = 1'})
        self.assertNotIsInstance(caught.exception, mcdk.ProtectedWindowError)
        self.assertTrue(client.last_execute_code_preflight['ok'])
        self.assertTrue(client.last_execute_code_preflight['execute_code_dispatched'])
        self.assertTrue(client.last_execute_code_preflight['python_return_checked'])
        self.assertFalse(client.last_execute_code_preflight['window_unavailable'])


if __name__ == '__main__':
    unittest.main()
