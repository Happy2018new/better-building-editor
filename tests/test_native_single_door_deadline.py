"""Bound every real client request and keep late/failed responses as evidence."""
import json
from pathlib import Path
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_native_single_door as probe


class Clock:
    def __init__(self):
        self.now = 0.
    def monotonic(self):
        return self.now
    def sleep(self, seconds):
        self.now += seconds


class Opener:
    def __init__(self, clock):
        self.clock = clock
        self.cost = .3
        self.requests = []
        self.list_not_ready = True
        self.error = None

    def open(self, request, timeout):
        payload = None if request.data is None else json.loads(request.data)
        method = request.get_method() if payload is None else payload['method']
        self.requests.append({'method': method, 'timeout': timeout, 'started': self.clock.now})
        result = {}
        if method == 'initialize':
            result = {'protocolVersion': '2025-03-26'}
        elif method == 'tools/list' and self.list_not_ready:
            self.list_not_ready = False
            result = None
        elif method == 'tools/call':
            result = {'structuredContent': {'return_value': 'token'}}
        body = {'id': None if payload is None else payload.get('id'), 'result': result}
        if result is None:
            body = {'id': payload['id'], 'error': {'code': -32000, 'message': 'Session not initialized'}}
        if self.error is not None:
            body = {'id': payload['id'], 'error': self.error}
        opener = self
        class Response:
            headers = {'Mcp-Session-Id': 'owned-session'}
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return None
            def read(self):
                opener.clock.now += opener.cost
                return json.dumps(body).encode('utf8')
        return Response()


class NativeSingleDoorDeadlineTests(unittest.TestCase):
    def client(self, clock, opener, journal, progress=lambda: None):
        binding = {'mcp_url': 'http://127.0.0.1:19133/mcp', 'token': 'token'}
        with mock.patch.object(probe.shapes.mcdk_wrapper, 'load_session', return_value=binding), \
             mock.patch.object(probe.shapes.mcdk_wrapper.urllib.request, 'build_opener', return_value=opener):
            return probe.DeadlineClient(4, journal, progress)

    def test_handshake_retry_binding_and_call_all_reclamp_each_actual_request(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic), \
             mock.patch.object(probe.time, 'sleep', clock.sleep), \
             mock.patch.object(probe.shapes.mcdk_wrapper, 'load_session', return_value={}), \
             mock.patch.object(probe.shapes, 'load_session', return_value={}):
            client = self.client(clock, opener, journal)
            client.__enter__()
            self.assertEqual(['initialize', 'notifications/initialized', 'tools/list', 'tools/list', 'tools/call'],
                             [row['method'] for row in opener.requests])
            self.assertEqual({'code': -32000, 'message': 'Session not initialized'}, journal[2]['native_error'])
            client.arm(clock.now + .8, 'fixture')
            client.call('execute_code', {'code': '_result=1', 'is_client': False, 'direct_return': True})
            self.assertAlmostEqual(.8, opener.requests[-2]['timeout'])
            self.assertAlmostEqual(.5, opener.requests[-1]['timeout'])
            self.assertTrue(all(row['timeout'] <= 2 for row in opener.requests))
            client.arm(clock.now + .1, 'close')
            client.close()
            self.assertEqual('DELETE', opener.requests[-1]['method'])
            self.assertAlmostEqual(.1, opener.requests[-1]['timeout'])
            self.assertIsNone(client.session)
            self.assertTrue(all(row['intent'] for row in journal))

    def test_late_response_is_preserved_but_never_accepted(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic):
            client = self.client(clock, opener, journal)
            client.arm(.3, 'load_handshake')
            with self.assertRaisesRegex(TimeoutError, 'response arrived after deadline'):
                client._post('initialize')
            self.assertTrue(journal[0]['response_received'])
            self.assertTrue(journal[0]['late_response'])
            self.assertIn('protocolVersion', journal[0]['result'])
            self.assertEqual(1, len(opener.requests))
            client.close()
            self.assertEqual(1, len(opener.requests))

    def test_native_error_is_kept_without_replaying_rpc(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        opener.error = {'code': -32603, 'message': 'original error', 'data': {'source': 'native'}}
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic):
            client = self.client(clock, opener, journal)
            with self.assertRaises(probe.shapes.mcdk_wrapper.RPCError):
                client._post('tools/call', {'name': 'execute_code', 'arguments': {}})
            self.assertEqual(opener.error, journal[0]['native_error'])
            self.assertEqual(1, len(opener.requests))

    def test_intent_persistence_consumes_deadline_without_sending_late_request(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        def progress():
            clock.now = 4
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic):
            client = self.client(clock, opener, journal, progress)
            with self.assertRaisesRegex(TimeoutError, 'persisting request intent'):
                client._post('initialize')
            self.assertEqual([], opener.requests)
            self.assertFalse(journal[0]['response_received'])

    def test_network_open_rechecks_deadline_after_binding_or_other_host_work(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic):
            client = self.client(clock, opener, journal)
            client.arm(.4, 'close')
            clock.now = .3
            client.opener.open(probe.urllib.request.Request(client.url, method='DELETE'), timeout=2)
            self.assertAlmostEqual(.1, opener.requests[0]['timeout'])
            clock.now = .4
            with self.assertRaisesRegex(TimeoutError, 'before network open'):
                client.opener.open(probe.urllib.request.Request(client.url, method='DELETE'), timeout=2)
            self.assertEqual(1, len(opener.requests))

    def test_binding_read_that_exhausts_deadline_cannot_send_requested_mutation(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic), \
             mock.patch.object(probe.time, 'sleep', clock.sleep), \
             mock.patch.object(probe.shapes.mcdk_wrapper, 'load_session', return_value={}):
            client = self.client(clock, opener, journal)
            client.__enter__()
            before = len(opener.requests)
            client.arm(clock.now + .3, 'fixture')
            with self.assertRaises(TimeoutError):
                client.call('execute_code', {'code': 'mutate_fixture()', 'is_client': False})
            self.assertEqual(before + 1, len(opener.requests))
            self.assertTrue(journal[-1]['late_response'])

    def test_close_refuses_network_when_owned_session_identity_validation_fails(self):
        clock, journal = Clock(), []
        opener = Opener(clock)
        with mock.patch.object(probe.time, 'monotonic', clock.monotonic), \
             mock.patch.object(probe.shapes, 'load_session', side_effect=RuntimeError('Owned PID reused')):
            client = self.client(clock, opener, journal)
            client.session = 'owned-session'
            client.close()
            self.assertEqual([], opener.requests)
            self.assertIn('Owned PID reused', client.close_error)
            self.assertIn('Owned PID reused', journal[0]['error'])


if __name__ == '__main__':
    unittest.main()
