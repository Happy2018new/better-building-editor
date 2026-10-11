"""Ensure native box diagnostics restore partial setup and wait for both layers."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import verify_native_plant_boxes as tool


class FakeClient:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeCheck:
    def __init__(self, *args):
        pass

    def run(self, code):
        return [0, 64, 0]


class NativePlantBoxToolTests(unittest.TestCase):
    def test_partial_setup_is_restored(self):
        state = {'fixture': False, 'cleanup': False}

        def server(client, code):
            if 'Previous native snow fixture' in code:
                state['fixture'] = True
                raise RuntimeError('setup failed after save')
            if 'hasattr(sys,' in code:
                return state['fixture']
            if 'GetBlockBasicInfo' in code:
                return {}
            if 'del sys._snow_visibility_native' in code:
                state['fixture'] = False
                state['cleanup'] = True
                return [{'clean': True}]
            self.fail('Unexpected server code')

        session = {'project': str(tool.ROOT), 'session_file': 'test-session', 'owner': 'test',
                   'game_pid': 1, 'game_identity': '1'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'report.json'
            with patch.object(tool, 'Client', FakeClient), patch.object(tool, 'BlueprintCheck', FakeCheck), \
                    patch.object(tool, 'load_session', return_value=session), \
                    patch.object(tool, 'server_run', side_effect=server):
                with self.assertRaisesRegex(RuntimeError, 'setup failed'):
                    tool.run(output, 1.)
            report = json.loads(output.read_bytes())
        self.assertTrue(state['cleanup'])
        self.assertTrue(report['restored'])
        self.assertFalse(report['completed'])

    def test_absent_fixture_does_not_mutate_world(self):
        with patch.object(tool, 'server_run', return_value=False) as server:
            self.assertTrue(tool.cleanup_fixture(object())[0]['clean'])
        self.assertEqual(server.call_count, 1)

    def test_replication_waits_for_correct_background_plant(self):
        class Check:
            def wait(self, label, predicate, read):
                self.stale_accepted = predicate({'front': ['minecraft:snow_layer', 8],
                                                'extra': ['minecraft:warped_roots']})
                row = {'front': ['minecraft:snow_layer', 8], 'extra': ['minecraft:crimson_roots']}
                self.correct_accepted = predicate(row)
                return row
        check = Check()
        tool.replicated(check, (6, 88, 6), 'minecraft:snow_layer', 'minecraft:crimson_roots')
        self.assertFalse(check.stale_accepted)
        self.assertTrue(check.correct_accepted)


if __name__ == '__main__':
    unittest.main()
