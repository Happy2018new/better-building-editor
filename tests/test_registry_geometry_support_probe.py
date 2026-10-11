"""Faults retain confirmed diagnostics and never turn uncertainty into support."""
import ast
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'behavior_pack'))
import probe_registry_geometry_support as probe


def batch_arguments(code):
    assignment = next(node for node in ast.parse(code).body if isinstance(node, ast.Assign)
                      and isinstance(node.targets[0], ast.Tuple))
    return ast.literal_eval(assignment.value)


def batch_result(names, prefix):
    defaults = dict(probe.catalogue()['materials'])
    rows = []
    for ordinal, name in enumerate(names):
        paths = []
        for kind in probe.KINDS:
            model = prefix + '_' + str(ordinal) + '_' + kind
            paths.append({'kind': kind, 'stage': 'recorded', 'status': 'supported',
                          'unsupported_mode': 1, 'requested_name': model,
                          'returned': model, 'api_supported': True})
        value = (name, defaults[name])
        rows.append({'material': list(value), 'states': probe.registry.states(value),
                     'status': 'recorded', 'paths': paths})
    return {'rows': rows, 'prefix': prefix, 'failure': None}


class FakeCheck:
    def __init__(self, fail_batch=None, malformed=False):
        self.batches = []
        self.fail_batch, self.malformed = fail_batch, malformed

    def run(self, code):
        if code == probe.CATALOGUE:
            return dict(deepcopy(probe.catalogue()), runtime='host-test-only')
        names, prefix = batch_arguments(code)
        self.batches.append(names)
        if len(self.batches) == self.fail_batch:
            raise TimeoutError('Response lost after dispatch')
        result = batch_result(names, prefix)
        if self.malformed:
            result['rows'][0]['paths'].pop()
        return result


class RegistryGeometrySupportProbeTests(unittest.TestCase):
    def test_default_invocation_is_one_64_name_batch_and_reports_limited_scope(self):
        report = probe.new_report(())
        check = FakeCheck()
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            probe.scan(check, output, report)
            saved = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual(1, len(check.batches))
        self.assertEqual(64, len(check.batches[0]))
        self.assertEqual(64, len(saved['rows']))
        self.assertEqual(128, saved['model_names_dispatched_upper_bound'])
        self.assertEqual(len(saved['expected_names']) - 64, len(saved['unexecuted_names']))
        self.assertFalse(saved['completed'])
        self.assertFalse(saved['all_catalogue_names'])
        self.assertFalse(saved['scope']['all_states'])
        self.assertTrue(saved['scope']['foreground_only'])
        self.assertFalse(saved['scope']['background_layer'])
        self.assertFalse(saved['visual_acceptance'])
        self.assertIsNone(saved['cache']['memory_bytes'])

    def test_lost_second_batch_preserves_first_and_separates_unknown_from_unexecuted(self):
        names = tuple(value[0] for value in probe.catalogue()['materials'][:130])
        report = probe.new_report(names)
        check = FakeCheck(fail_batch=2)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            probe.scan(check, output, report, max_batches=3)
            saved = json.loads(output.read_text(encoding='utf8'))
            self.assertEqual(64, len(saved['rows']))
            self.assertEqual(set(names[64:128]), set(saved['uncertain_names']))
            self.assertEqual(list(names[128:]), saved['unexecuted_names'])
            self.assertEqual([], saved['failed_names'])
            self.assertEqual('batch_request', saved['errors'][-1]['stage'])
            self.assertIn('TimeoutError', saved['errors'][-1]['traceback'])
            self.assertEqual('recorded', saved['batches'][0]['status'])
            self.assertEqual('uncertain', saved['batches'][1]['status'])
            resumed = probe.load_report(output, names)
            continuation = FakeCheck()
            probe.scan(continuation, output, resumed)
            self.assertEqual([names[128:]], continuation.batches)
            self.assertEqual(set(names[64:128]), set(resumed['uncertain_names']))
        self.assertEqual(2, len(check.batches))
        self.assertFalse(saved['completed'])
        self.assertEqual([], probe.summarize(saved)['unsupported']['state_only'])

    def test_bad_path_coverage_remains_uncertain_instead_of_marking_missing_unsupported(self):
        names = tuple(value[0] for value in probe.catalogue()['materials'][:2])
        report = probe.new_report(names)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            probe.scan(FakeCheck(malformed=True), output, report)
            saved = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual([], saved['rows'])
        self.assertEqual(set(names), set(saved['uncertain_names']))
        self.assertEqual([], saved['failed_names'])
        self.assertEqual('batch_response', saved['errors'][-1]['stage'])

    def test_client_initialization_failure_is_persisted_before_any_batch(self):
        name = probe.catalogue()['materials'][0][0]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            identity = {'manifest_sha256': 'owned-test-session', 'owner': 'host-test-only'}
            with mock.patch.object(probe, 'Client') as client, mock.patch('sys.stdout', io.StringIO()), \
                    mock.patch.object(probe, 'session_identity', return_value=identity):
                client.return_value.__enter__.side_effect = RuntimeError('No owned session')
                code = probe.main([str(output), '--names', name])
            saved = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual(1, code)
        self.assertEqual([name], saved['unexecuted_names'])
        self.assertEqual([], saved['uncertain_names'])
        self.assertEqual('client_session', saved['errors'][-1]['stage'])
        self.assertIn('No owned session', saved['errors'][-1]['traceback'])
        self.assertFalse(saved['completed'])

    def test_changed_session_manifest_cannot_resume_an_existing_report(self):
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / 'session.json'
            output = Path(directory) / 'support.json'
            session.write_text('{"game_identity":"original"}', encoding='utf8')
            with mock.patch.dict(probe.os.environ, MCDEV_SESSION_FILE=str(session), MCDEV_OWNER='host-test'):
                probe.checkpoint(output, probe.new_report(()))
                previous = output.read_bytes()
                session.write_text('{"game_identity":"replacement"}', encoding='utf8')
                with self.assertRaisesRegex(ValueError, 'session_identity'):
                    probe.load_report(output, ())
                self.assertEqual(previous, output.read_bytes())

    def test_changed_api_runtime_is_rejected_before_generating_more_geometry(self):
        report = probe.new_report(())
        report['runtime'] = 'previous-game-runtime'
        check = FakeCheck()
        with tempfile.TemporaryDirectory() as directory:
            probe.scan(check, Path(directory) / 'support.json', report)
        self.assertEqual([], check.batches)
        self.assertEqual([], report['uncertain_names'])
        self.assertEqual('catalogue', report['errors'][-1]['stage'])
        self.assertEqual('previous-game-runtime', report['runtime'])

    def test_checkpoint_failure_before_dispatch_keeps_names_unexecuted(self):
        names = tuple(value[0] for value in probe.catalogue()['materials'][:2])
        report, check = probe.new_report(names), FakeCheck()
        replace = probe.os.replace
        calls = []

        def fail_first_replace(source, target):
            calls.append((source, target))
            if len(calls) == 1:
                raise OSError('Dispatch checkpoint unavailable')
            return replace(source, target)

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            with mock.patch.object(probe.os, 'replace', side_effect=fail_first_replace):
                probe.scan(check, output, report)
            saved = json.loads(output.read_text(encoding='utf8'))
        self.assertEqual([], check.batches)
        self.assertEqual([], saved['uncertain_names'])
        self.assertEqual(list(names), saved['unexecuted_names'])
        self.assertEqual(0, saved['model_names_dispatched_upper_bound'])
        self.assertEqual('checkpoint_before_dispatch', saved['errors'][-1]['stage'])

    def execute_native_probe(self, names, geometry, deserialized=True):
        class Palette:
            def DeserializeBlockPalette(self, data):
                self.data = data
                return deserialized

            def SerializeBlockPalette(self):
                return self.data

        block = types.SimpleNamespace(GetBlankBlockPalette=Palette)
        factory = types.SimpleNamespace(CreateBlock=lambda level: block,
                                        CreateBlockGeometry=lambda level: geometry)
        bridge = types.ModuleType('modern_projection.projection.bridge')
        bridge._native_palette = lambda data: data
        scope = {'b': types.SimpleNamespace(factory=factory, level='host-test-only'), 'json': json}
        with mock.patch.dict(sys.modules, {'modern_projection.projection.bridge': bridge}):
            exec(probe.PROBE % (names, 'host_test'), scope)
        return json.loads(scope['_result'])

    def test_sdk_exception_preserves_raw_result_and_actual_native_failure_stage(self):
        class Geometry:
            def __init__(self):
                self.calls = 0

            def CombineBlockPaletteToGeometry(self, palette, name, mode):
                self.calls += 1
                if self.calls == 2:
                    raise RuntimeError('Native prepared failure')
                return name

        result = self.execute_native_probe(('minecraft:stone',), Geometry())
        probe.validate_batch(result, ('minecraft:stone',), 'host_test')
        row = result['rows'][0]
        self.assertEqual('failed', row['status'])
        self.assertEqual('supported', row['paths'][0]['status'])
        failed = row['paths'][1]
        self.assertEqual('combine', failed['stage'])
        self.assertIsNone(failed['api_supported'])
        self.assertIn('Native prepared failure', failed['traceback'])

    def test_strict_none_is_unsupported_and_proxy_submission_is_attributed(self):
        geometry = types.SimpleNamespace(CombineBlockPaletteToGeometry=lambda palette, name, mode: None)
        result = self.execute_native_probe(('minecraft:short_grass',), geometry)
        probe.validate_batch(result, ('minecraft:short_grass',), 'host_test')
        row = result['rows'][0]
        self.assertEqual('recorded', row['status'])
        self.assertTrue(all(path['status'] == 'unsupported' for path in row['paths']))
        self.assertEqual([], row['paths'][0]['submission']['proxy_materials'])
        self.assertIn('modern_projection:preview_short_grass',
                      row['paths'][1]['submission']['proxy_materials'])
        self.assertFalse(row['paths'][1]['submission']['original_material_retained'])

    def test_deserialize_false_is_a_failure_without_a_combine_attempt(self):
        geometry = types.SimpleNamespace(CombineBlockPaletteToGeometry=mock.Mock())
        result = self.execute_native_probe(('minecraft:stone',), geometry, deserialized=False)
        probe.validate_batch(result, ('minecraft:stone',), 'host_test')
        self.assertEqual('failed', result['rows'][0]['status'])
        self.assertTrue(all(path['stage'] == 'deserialize' and path['status'] == 'failed'
                            and path['api_supported'] is None for path in result['rows'][0]['paths']))
        geometry.CombineBlockPaletteToGeometry.assert_not_called()

    def test_atomic_checkpoint_failure_keeps_previous_artifact_readable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'support.json'
            probe.checkpoint(output, {'sequence': 1})
            with mock.patch.object(probe.os, 'replace', side_effect=OSError('Destination unavailable')):
                with self.assertRaises(OSError):
                    probe.checkpoint(output, {'sequence': 2})
            self.assertEqual({'sequence': 1}, json.loads(output.read_text(encoding='utf8')))
            self.assertEqual(1, len(list(Path(directory).glob('*.tmp'))))


if __name__ == '__main__':
    unittest.main()
