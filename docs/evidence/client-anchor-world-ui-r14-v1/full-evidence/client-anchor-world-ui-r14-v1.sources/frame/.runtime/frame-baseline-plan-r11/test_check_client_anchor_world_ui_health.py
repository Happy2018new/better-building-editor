"""Offline checks that timer failure still reaches bounded owner cleanup."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import urllib.request

import check_client_anchor_world_ui_health as health


class HealthTests(unittest.TestCase):
    def exercise(self, fail_start=False, fail_persistence=False):
        with tempfile.TemporaryDirectory(prefix='anchor-health-review-') as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            (bundle / 'plan.json').write_text(json.dumps({'nonce': '1' * 32}), encoding='ascii')
            calls, state = [], {'clock': 100., 'identity': 0, 'timer_mutated': False}
            reports = []

            class Guard:
                source, window = root, {'hwnd': 29102794}

                def __init__(self, *args):
                    pass

                def guard(self):
                    return {'background_safe': True}

                def verify_pack(self, *args):
                    pass

            class Opener:
                def open(self, request, timeout):
                    calls.append(('network', request.get_method(), timeout))
                    return SimpleNamespace(status=200)

            class Client:
                def __init__(self, timeout):
                    self.timeout, self.counter = timeout, 0
                    self.opener = Opener()
                    self.binding = {'game_pid': 44536, 'token': 'owner-token'}

                def __enter__(self):
                    self._post('initialize')
                    return self

                def _post(self, method, params=None, notification=False):
                    self.counter += 1
                    self.opener.open(urllib.request.Request('http://owned.invalid/mcp', data=b'{}'), timeout=self.timeout)
                    if method == 'initialize':
                        return {'isError': False}
                    code = params['arguments']['code']
                    if 'game.AddTimer' in code:
                        calls.append('start')
                        state['timer_mutated'] = True
                        if fail_start:
                            state['clock'] = 125.
                            raise RuntimeError('timer initialization failed after possible mutation')
                        value = {'started': 1., 'callbacks': []}
                    elif 'delattr(sys,marker)' in code:
                        calls.append('stop')
                        value = {'owned': True, 'restored': True, 'started': 1., 'callbacks': [1.2, 1.4], 'now': 2.}
                    else:
                        state['identity'] += 1
                        value = {'runtime': '1.21', 'pid': 44536, 'token': 'owner-token', 'now': float(state['identity'])}
                    return {'isError': False, 'structuredContent': {'return_value': value}}

                def call(self, name, arguments):
                    return self._post('tools/call', {'name': name, 'arguments': arguments})

                def close(self):
                    self.opener.open(urllib.request.Request('http://owned.invalid/mcp', method='DELETE'), timeout=2.)
                    calls.append('close')

            def transport(underlying, request, timeout, deadline, clock, finished):
                response = underlying.open(request, timeout)
                finished()
                return response

            def save(path, report):
                reports.append(report)
                if fail_persistence and state['timer_mutated']:
                    raise OSError('persistent storage failure after timer setup')
                path.write_text(json.dumps(report), encoding='ascii')

            with patch.object(health, 'ARTIFACTS', root), patch.object(health, 'BUNDLE', bundle), \
                    patch.object(health, 'SessionPackStage', Guard), patch.object(health, 'Client', Client), \
                    patch.object(health, 'absolute_http_open', side_effect=transport), \
                    patch.object(health, 'save', side_effect=save), \
                    patch.object(health.time, 'monotonic', side_effect=lambda: state['clock']), \
                    patch.object(health.time, 'sleep'):
                result = health.child(100.)
            report = reports[-1] if fail_persistence else json.loads((root / (health.EVIDENCE_PREFIX + '.post-restoration-health.json')).read_bytes())
            self.assertEqual(1, calls.count('start'))
            self.assertEqual(1, calls.count('stop'))
            self.assertEqual(1, calls.count('close'))
            self.assertEqual('DELETE', report['network_requests'][-1]['http_method'])
            self.assertTrue(report['timer_cleanup_verified'])
            self.assertEqual(130., report['cleanup_deadline_monotonic'])
            self.assertFalse(report['fixture_mutation_attempted'])
            return result, report

    def test_fresh_client_and_server_clocks_and_two_callbacks(self):
        result, report = self.exercise()
        self.assertEqual(0, result)
        self.assertTrue(report['passed'])
        self.assertGreater(report['client_after']['now'], report['client_before']['now'])
        self.assertGreater(report['server_after']['now'], report['server_before']['now'])

    def test_partial_timer_start_failure_cleanup_uses_reserve_without_retry(self):
        result, report = self.exercise(fail_start=True)
        self.assertEqual(1, result)
        self.assertFalse(report['passed'])
        self.assertIn('possible mutation', report['errors'][0])
        self.assertFalse(report['cleanup_errors'])
        self.assertEqual(25., report['elapsed_seconds'])

    def test_persistent_report_failure_after_timer_setup_still_cleans_and_closes(self):
        result, report = self.exercise(fail_persistence=True)
        self.assertEqual(1, result)
        self.assertFalse(report['passed'])
        self.assertTrue(report['timer_cleanup_verified'])
        self.assertTrue(any('persistent storage failure' in error for error in report['cleanup_errors']))
        self.assertEqual('DELETE', report['network_requests'][-1]['http_method'])


if __name__ == '__main__':
    unittest.main()
