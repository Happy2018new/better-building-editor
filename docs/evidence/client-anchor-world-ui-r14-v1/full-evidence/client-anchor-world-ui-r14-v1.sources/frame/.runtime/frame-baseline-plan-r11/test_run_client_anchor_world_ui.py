"""Offline owner checks for normal, actual-network, cleanup and supervisor budgets."""
import json
from pathlib import Path
import subprocess
import threading
import time
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import run_client_anchor_world_ui as owner


class OwnerTests(unittest.TestCase):
    def exercise(self, mode=None):
        with tempfile.TemporaryDirectory(prefix='client-anchor-owner-review-') as directory:
            root = Path(directory)
            source = root / 'probe.py'
            source.write_bytes(b'offline reviewed source\n')
            output, runtime_output = root / 'owner.json', root / 'runtime.json'
            calls, state = [], {'clock': 100., 'write_failed': False}
            memory_reports = []

            class Guard:
                source = root
                window = {'hwnd': 29102794, 'width': 1994, 'height': 1105}

                def guard(self):
                    calls.append('guard')
                    return {'background_safe': True}

                def verify_pack(self, *args):
                    calls.append('pack_verify')

            class Opener:
                def open(self, request, timeout):
                    calls.append(('network', request.get_method(), timeout))
                    return SimpleNamespace(status=200)

            class Client:
                def __init__(self, timeout):
                    self.timeout, self.counter, self.session = timeout, 0, 'offline-session'
                    self.opener = Opener()

                def __enter__(self):
                    calls.append('binding')
                    self._post('tools/call', {'name': 'execute_code', 'arguments': {'code': 'token'}})
                    return self

                def _post(self, method, params, notification=False):
                    self.counter += 1
                    if mode == 'actual_expired':
                        state['clock'] = 190.1
                    if mode == 'actual_remaining':
                        state['clock'] = 189.
                    self.opener.open(urllib.request.Request('http://owned.invalid/mcp', data=b'{}'),
                                     timeout=self.timeout)
                    if mode == 'raw_error':
                        return {'isError': True, 'content': [{'type': 'text', 'text': 'owned bind rejected'}]}
                    return {'isError': False, 'content': [{'type': 'text', 'text': 'true'}]}

                def close(self):
                    calls.append('close')
                    try:
                        self.opener.open(urllib.request.Request('http://owned.invalid/mcp', method='DELETE'),
                                         timeout=2.)
                    except Exception:
                        pass
                    self.session = None

            def execute(bundle, path, check, guard, deadline):
                calls.append('probe')
                self.assertEqual(220., deadline)
                if mode == 'uncertain':
                    raise RuntimeError('uncertain owned setter; no replay')
                if mode == 'cleanup':
                    state['clock'] = 205.
                    check.client.frame_dispatch_deadline = deadline
                if mode == 'cleanup_expired':
                    state['clock'] = 220.1
                    check.client.frame_dispatch_deadline = deadline
                if mode == 'persistent_cleanup':
                    check.client.frame_dispatch_deadline = deadline
                    state['write_failed'] = True
                if mode == 'persistent_normal':
                    state['write_failed'] = True
                if mode in ('persistent_cleanup', 'persistent_normal'):
                    try:
                        check.client._post('tools/call', {'name': 'execute_code',
                                                        'arguments': {'code': 'normal owned probe'}})
                    except OSError:
                        calls.append('normal_write_failed')
                    check.client.frame_dispatch_deadline = deadline
                    for operation in ('remove', 'pop', 'destroy'):
                        check.client._post('tools/call', {'name': 'execute_code',
                                                        'arguments': {'code': 'owned cleanup ' + operation}})
                        calls.append(operation)
                    report = {'completed': False, 'restored': True, 'errors': [], 'cleanup_errors': []}
                    path.write_text(json.dumps(report), encoding='ascii')
                    return report
                response = check.client._post('tools/call', {'name': 'execute_code',
                                                           'arguments': {'code': 'owned probe'}})
                raw_error = response.get('isError', False)
                report = {'completed': not raw_error, 'restored': True,
                          'errors': ['raw native error'] if raw_error else [], 'cleanup_errors': []}
                path.write_text(json.dumps(report), encoding='ascii')
                return report

            probe = SimpleNamespace(preflight=lambda *args: None, execute_probe=execute)

            def fake_transport(underlying, request, timeout, deadline, clock, finished):
                response = underlying.open(request, timeout=timeout)
                finished()
                return response

            def save(path, report):
                memory_reports.append(report)
                if state['write_failed']:
                    raise OSError('persistent owner journal write failure')
                path.write_text(json.dumps(report), encoding='ascii')

            with patch.object(owner, 'Client', Client), \
                    patch.object(owner, 'SignCheck', side_effect=lambda client, *a, **kw: SimpleNamespace(client=client)), \
                    patch.object(owner, 'absolute_http_open', side_effect=fake_transport), \
                    patch.object(owner, 'save', side_effect=save), \
                    patch.object(owner, 'verify_loaded_resources', return_value={'resources': 'unchanged'}), \
                    patch.object(owner, 'source_config_hashes', return_value={'config': 'unchanged'}):
                report = owner.execute_once(probe, source, output, runtime_output, Guard(), started=100.,
                                            clock=lambda: state['clock'])
            if mode in ('persistent_cleanup', 'persistent_normal'):
                self.assertIs(report, memory_reports[-1])
            else:
                self.assertEqual(report, json.loads(output.read_bytes()))
            self.assertEqual(1, calls.count('close'))
            self.assertFalse(report['shader_or_pack_mutation_attempted'])
            self.assertFalse(report['world_or_inventory_mutation_attempted'])
            self.assertFalse(report['player_position_mutation_attempted'])
            self.assertFalse(report['production_rendering_accepted'])
            self.assertFalse(report['editor_frame_content_accepted'])
            self.assertFalse(report['enchantment_glint_accepted'])
            self.assertTrue(report['protected_sources_and_configs_unchanged'])
            return report, calls

    def test_absolute_response_budget_interrupts_continuously_streamed_body(self):
        self.check_slow_stream(headers=False)

    def test_absolute_response_budget_interrupts_continuously_streamed_headers(self):
        self.check_slow_stream(headers=True)

    def check_slow_stream(self, headers):
        class SlowResponse(BaseHTTPRequestHandler):
            def do_GET(self):
                try:
                    if headers:
                        self.wfile.write(b'HTTP/1.1 200 OK\r\nX-Drip: ')
                    else:
                        self.send_response(200)
                        self.send_header('Content-Length', '1000')
                        self.end_headers()
                    for _ in range(50):
                        self.wfile.write(b'x')
                        self.wfile.flush()
                        time.sleep(.03)
                except (ConnectionError, OSError):
                    pass

            def log_message(self, *args):
                pass

        server = ThreadingHTTPServer(('127.0.0.1', 0), SlowResponse)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        errors = []
        started = time.monotonic()
        try:
            request = urllib.request.Request('http://127.0.0.1:%s/' % server.server_port)
            with self.assertRaises(Exception):
                with owner.absolute_http_open(None, request, .15, started + 1., time.monotonic, errors.append) as response:
                    response.read()
            self.assertLess(time.monotonic() - started, .8)
            self.assertEqual(1, len(errors))
            self.assertIsNotNone(errors[0])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=1.)

    def test_completed_probe_preserves_sources_and_deadline_contract(self):
        report, calls = self.exercise()
        self.assertTrue(report['completed'] and report['restored'])
        self.assertEqual([190., 220., 250.], [report[key] for key in
                         ('normal_deadline_monotonic', 'cleanup_deadline_monotonic', 'outer_deadline_monotonic')])
        self.assertEqual(1, calls.count('probe'))
        self.assertEqual('DELETE', report['network_requests'][-1]['http_method'])

    def test_raw_native_error_and_request_ids_are_preserved(self):
        report, _ = self.exercise('raw_error')
        self.assertFalse(report['completed'])
        self.assertTrue(report['restored'])
        self.assertEqual([1, 2], [row['request']['id'] for row in report['requests']])
        self.assertTrue(all(row['response']['isError'] for row in report['requests']))

    def test_actual_network_open_rechecks_deadline_after_protected_preflight(self):
        report, calls = self.exercise('actual_expired')
        self.assertFalse(report['completed'])
        self.assertEqual(0, calls.count('probe'))
        self.assertEqual(['DELETE'], [row[1] for row in calls if isinstance(row, tuple)])
        self.assertIn('Actual network request deadline exhausted', report['network_requests'][0]['error'])

    def test_actual_network_timeout_uses_remaining_time_after_preflight(self):
        report, calls = self.exercise('actual_remaining')
        self.assertTrue(report['completed'])
        self.assertEqual([1., 1.], [row[2] for row in calls if isinstance(row, tuple) and row[1] == 'POST'])

    def test_cleanup_dispatch_uses_reserved_deadline(self):
        report, _ = self.exercise('cleanup')
        self.assertTrue(report['completed'] and report['restored'])
        self.assertEqual(105., report['native_elapsed_seconds'])

    def test_expired_cleanup_blocks_sdk_but_allows_session_close(self):
        report, calls = self.exercise('cleanup_expired')
        self.assertFalse(report['completed'] or report['restored'])
        self.assertEqual(['POST', 'DELETE'], [row[1] for row in calls if isinstance(row, tuple)])
        self.assertIn('dispatch deadline exhausted', report['requests'][-1]['error'])

    def test_uncertain_native_operation_is_not_replayed(self):
        report, calls = self.exercise('uncertain')
        self.assertFalse(report['completed'] or report['restored'])
        self.assertEqual(1, calls.count('probe'))

    def test_persistent_cleanup_journal_failure_still_dispatches_owned_remove_pop_destroy_and_delete(self):
        report, calls = self.exercise('persistent_cleanup')
        self.assertFalse(report['restored'])
        self.assertTrue(any('persistent owner journal' in error for error in report['cleanup_errors']))
        self.assertEqual([1, 1, 1], [calls.count(operation) for operation in ('remove', 'pop', 'destroy')])
        self.assertEqual('DELETE', report['network_requests'][-1]['http_method'])

    def test_persistent_normal_journal_failure_blocks_normal_call_but_preserves_cleanup(self):
        report, calls = self.exercise('persistent_normal')
        self.assertEqual(1, calls.count('normal_write_failed'))
        self.assertEqual([1, 1, 1], [calls.count(operation) for operation in ('remove', 'pop', 'destroy')])
        self.assertFalse(report['restored'])
        self.assertEqual('DELETE', report['network_requests'][-1]['http_method'])

    def test_outer_supervisor_uses_one_remaining_budget_and_never_retries(self):
        with tempfile.TemporaryDirectory(prefix='client-anchor-supervisor-review-') as directory:
            output = Path(directory) / 'supervisor.json'
            calls = []

            def blocked(command, **options):
                calls.append((command, options))
                raise subprocess.TimeoutExpired(command, options['timeout'])

            report = owner.supervise(output, started=100., clock=lambda: 101., run=blocked)
            self.assertEqual(1, len(calls))
            self.assertEqual(149., calls[0][1]['timeout'])
            self.assertEqual('100.0', calls[0][1]['env'][owner.START_ENV])
            self.assertTrue(report['timed_out'])
            self.assertFalse(report['completed'] or report['cleanup_verified'])
            self.assertTrue(report['unresolved_runtime_requires_owner_review'])
            self.assertEqual(report, json.loads(output.read_bytes()))


if __name__ == '__main__':
    unittest.main()
