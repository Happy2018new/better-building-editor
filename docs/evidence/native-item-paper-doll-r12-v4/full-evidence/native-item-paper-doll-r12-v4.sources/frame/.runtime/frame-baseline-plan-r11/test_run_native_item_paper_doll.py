"""Verify raw native errors and one-shot owner cleanup without a managed game."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import run_native_item_paper_doll as owner


class OwnerTests(unittest.TestCase):
    def exercise(self, failure=None):
        with tempfile.TemporaryDirectory(prefix='native-item-owner-review-') as directory:
            root = Path(directory)
            source = root / 'probe.py'
            source.write_bytes(b'offline reviewed source\n')
            output, runtime_output = root / 'owner.json', root / 'runtime.json'
            calls, state = [], {'clock': 100.}

            class Guard:
                source = root
                window = {'hwnd': 29102794, 'width': 1994, 'height': 1105}

                def guard(self):
                    calls.append('guard')
                    return {'background_safe': True}

                def verify_pack(self, *args):
                    calls.append('pack_verify')

            class Client:
                def __init__(self, timeout):
                    self.timeout, self.counter = timeout, 0

                def __enter__(self):
                    calls.append('binding')
                    self._post('tools/call', {'name': 'execute_code', 'arguments': {'code': 'token'}})
                    return self

                def _post(self, method, params, notification=False):
                    self.counter += 1
                    calls.append('rpc')
                    if failure == 'raw_error':
                        return {'isError': True, 'content': [{'type': 'text',
                                 'text': 'Code execution failed: list assignment index out of range'}]}
                    return {'isError': False, 'content': [{'type': 'text', 'text': 'true'}]}

                def close(self):
                    calls.append('close')

            def execute(bundle, path, check, guard, deadline):
                calls.append('probe')
                if failure == 'raise':
                    raise RuntimeError('uncertain native bind; no replay')
                if failure == 'deadline':
                    state['clock'] = deadline + .1
                response = check.client._post('tools/call', {'name': 'execute_code',
                                                           'arguments': {'code': 'owned probe'}})
                raw_error = response.get('isError', False)
                report = {'completed': not raw_error, 'restored': True,
                          'errors': ['raw native error'] if raw_error else [], 'cleanup_errors': []}
                path.write_text(json.dumps(report), encoding='ascii')
                return report

            probe = SimpleNamespace(preflight=lambda *args: None, execute_probe=execute)
            with patch.object(owner, 'Client', Client), \
                    patch.object(owner, 'SignCheck', side_effect=lambda client, *a, **kw: SimpleNamespace(client=client)), \
                    patch.object(owner, 'source_config_hashes', return_value={'config': 'unchanged'}):
                report = owner.execute_once(probe, source, output, runtime_output, Guard(),
                                            clock=lambda: state['clock'])
            self.assertEqual(report, json.loads(output.read_bytes()))
            self.assertEqual(1, calls.count('close'))
            self.assertEqual(1, calls.count('probe'))
            self.assertFalse(report['shader_or_pack_mutation_attempted'])
            self.assertFalse(report['world_or_inventory_mutation_attempted'])
            self.assertFalse(report['production_rendering_accepted'])
            self.assertFalse(report['enchantment_glint_accepted'])
            self.assertTrue(report['protected_sources_and_configs_unchanged'])
            return report, calls

    def test_complete_probe_closes_client_and_preserves_source_state(self):
        report, calls = self.exercise()
        self.assertTrue(report['completed'])
        self.assertTrue(report['restored'])

    def test_raw_error_content_and_request_id_are_preserved(self):
        report, calls = self.exercise('raw_error')
        self.assertFalse(report['completed'])
        self.assertTrue(report['restored'])
        self.assertEqual(2, len(report['requests']))
        self.assertEqual([1, 2], [row['request']['id'] for row in report['requests']])
        for row in report['requests']:
            self.assertTrue(row['response']['isError'])
            self.assertIn('list assignment index out of range', row['response']['content'][0]['text'])

    def test_uncertain_probe_exception_is_not_replayed(self):
        report, calls = self.exercise('raise')
        self.assertFalse(report['completed'])
        self.assertFalse(report['restored'])
        self.assertEqual(1, len(report['errors']))

    def test_expired_deadline_blocks_actual_rpc_but_retains_attempt(self):
        report, calls = self.exercise('deadline')
        self.assertFalse(report['completed'])
        self.assertFalse(report['restored'])
        self.assertEqual(1, calls.count('rpc'))
        self.assertEqual(2, len(report['requests']))
        self.assertIn('deadline exhausted', report['requests'][-1]['error'])


if __name__ == '__main__':
    unittest.main()
