"""Discovery retries are bounded and retain evidence without another launch."""
import copy
from contextlib import ExitStack, nullcontext
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances
import _window as window


class Clock:
    def __init__(self):
        self.now = 0
        self.sleeps = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


class DiscoveryTimeoutTests(unittest.TestCase):
    def test_discovery_uses_longer_cap_or_the_callers_remaining_budget(self):
        response = SimpleNamespace(returncode=0, stdout=b'{"children":[42],"listeners":[17]}', stderr=b'')
        with patch.object(instances.subprocess, 'run', return_value=response) as run:
            self.assertEqual({'children': [42], 'listeners': [17]}, instances.discover(17, 1234))
            self.assertEqual(20, run.call_args.kwargs['timeout'])
            instances.discover(17, 1234, timeout=2.75)
        self.assertEqual(2.75, run.call_args.kwargs['timeout'])
        self.assertEqual(subprocess.CREATE_NO_WINDOW, run.call_args.kwargs['creationflags'])
        command = run.call_args.args[0]
        self.assertEqual(['powershell.exe', '-NoProfile', '-Command'], command[:3])
        self.assertIn('ParentProcessId=17', command[3])
        self.assertIn('-LocalPort 1234', command[3])

    def test_discovery_retains_process_errors_and_timeout_details(self):
        response = SimpleNamespace(returncode=1, stdout=b'', stderr=b'cim query failed')
        with patch.object(instances.subprocess, 'run', return_value=response):
            with self.assertRaisesRegex(RuntimeError, 'cim query failed'):
                instances.discover(17, 1234)
        error = subprocess.TimeoutExpired(['powershell.exe'], 2, output=b'partial', stderr=b'provider busy')
        with patch.object(instances.subprocess, 'run', side_effect=error):
            with self.assertRaises(subprocess.TimeoutExpired) as failure:
                instances.discover(17, 1234, timeout=2)
        self.assertIs(error, failure.exception)
        self.assertEqual(b'partial', failure.exception.output)
        self.assertEqual(b'provider busy', failure.exception.stderr)


class BackgroundStartupBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        (self.folder / 'game.exe').write_bytes(b'host fixture, never executed')
        self.args = SimpleNamespace(project=str(self.folder), mcdk='fixture-mcdk.exe',
            game_exe='game.exe', name='host-budget', owner='host-budget',
            port=None, preset=None, wait=35)
        self.clock = Clock()
        self.process = SimpleNamespace(pid=17, returncode=None, poll=lambda: None)
        self.snapshot = {'hwnd': 101, 'pid': 20, 'identity': 'editor-created', 'process': 'editor.exe'}
        self.records = []
        stack = ExitStack()
        self.addCleanup(stack.close)

        def replace(target, name, **kwargs):
            return stack.enter_context(patch.object(target, name, **kwargs))

        replace(instances, 'resolve_mcdk', return_value='fixture-mcdk.exe')
        replace(instances, 'resolve_game', return_value='game.exe')
        replace(instances, 'noactivate_contract', return_value=None)
        replace(instances, 'registry_dir', return_value=self.folder / 'registry')
        replace(instances, 'file_lock', return_value=nullcontext())
        replace(instances, 'create_probe', return_value=str(self.folder / 'probe'))
        replace(instances, 'prepare_world', return_value=(self.folder / 'world', self.folder / 'world-link'))
        replace(instances, 'foreground_snapshot', return_value=self.snapshot)
        replace(instances, 'validate_foreground_snapshot', return_value=True)
        replace(instances, 'process_identity', side_effect=lambda pid: 'created-' + str(pid))
        replace(instances.time, 'monotonic', side_effect=self.clock.monotonic)
        replace(instances.time, 'sleep', side_effect=self.clock.sleep)
        self.spawn = replace(instances.subprocess, 'Popen', return_value=self.process)
        self.terminate = replace(instances, 'terminate_owned')
        self.activate = replace(window, '_activate_window')
        self.run = replace(instances.subprocess, 'run')
        original_write = instances.write_json

        def write(path, data):
            original_write(path, data)
            if Path(path).name == 'session.json':
                self.records.append(copy.deepcopy(data))

        replace(instances, 'write_json', side_effect=write)
        replace(instances, 'return_value', side_effect=lambda value: value)
        self.client = replace(instances, 'Client')
        self.client.return_value.__enter__.return_value.call.side_effect = self.runtime_reply

    def runtime_reply(self, tool, arguments):
        self.assertEqual('execute_code', tool)
        session = self.records[-1]
        if arguments['code'].startswith('import os'):
            return {'pid': 42, 'appdata': session['appdata']}
        return session['token']

    def query(self, command, **kwargs):
        self.clock.now += 8.87
        return SimpleNamespace(returncode=0, stdout=b'{"children":[42],"listeners":[17]}', stderr=b'')

    def timeout(self, command, **kwargs):
        self.clock.now += kwargs['timeout']
        raise subprocess.TimeoutExpired(command, kwargs['timeout'],
                                        output=b'partial children', stderr=b'provider busy')

    def assert_retained(self, result):
        self.assertEqual(result, json.loads(Path(result['session_file']).read_text(encoding='utf-8')))
        self.assertEqual(17, result['mcdk_pid'])
        self.assertEqual('created-17', result['mcdk_identity'])
        self.assertTrue(result['foreground_unchanged'])
        self.spawn.assert_called_once()
        self.terminate.assert_not_called()
        self.activate.assert_not_called()

    def test_transient_timeout_recovers_with_remaining_budget_and_retains_evidence(self):
        attempts = iter((self.timeout, self.query))
        self.run.side_effect = lambda *args, **kwargs: next(attempts)(*args, **kwargs)
        result = instances.start(self.args)
        self.assertEqual('ready', result['state'])
        self.assertTrue(result['ready'])
        self.assertEqual([20, 14.5], [call.kwargs['timeout'] for call in self.run.call_args_list])
        self.assertAlmostEqual(29.37, self.clock.now)
        record = result['discovery_timeouts'][0]
        self.assertEqual(1, record['attempt'])
        self.assertEqual(20, record['timeout_seconds'])
        self.assertEqual(20, record['elapsed_seconds'])
        self.assertEqual('partial children', record['stdout'])
        self.assertEqual('provider busy', record['stderr'])
        self.assertEqual(self.run.call_args_list[0].args[0], record['command'])
        self.assertIn('timed out', record['error'])
        self.assert_retained(result)

    def test_slow_discovery_finishes_beyond_former_cap_without_retry(self):
        def slow_reply(command, **kwargs):
            if kwargs['timeout'] < 12.5:
                return self.timeout(command, **kwargs)
            self.clock.now += 12.5
            return SimpleNamespace(returncode=0, stdout=b'{"children":[42],"listeners":[17]}', stderr=b'')

        self.run.side_effect = slow_reply
        result = instances.start(self.args)
        self.assertEqual('ready', result['state'])
        self.assertEqual(12.5, self.clock.now)
        self.run.assert_called_once()
        self.assertNotIn('discovery_timeouts', result)
        self.assert_retained(result)

    def test_repeated_timeout_stops_at_wait_deadline_with_last_error_and_owned_identity(self):
        self.args.wait = 24
        self.run.side_effect = self.timeout
        result = instances.start(self.args)
        self.assertEqual('failed', result['state'])
        self.assertFalse(result['ready'])
        self.assertEqual([20, 3.5], [call.kwargs['timeout'] for call in self.run.call_args_list])
        self.assertEqual(24, self.clock.now)
        self.assertEqual([1, 2], [record['attempt'] for record in result['discovery_timeouts']])
        self.assertEqual(result['discovery_timeouts'][-1]['error'], result['error'])
        self.client.assert_not_called()
        self.assert_retained(result)

    def test_short_wait_clamps_first_query_and_does_not_begin_readiness_after_deadline(self):
        self.args.wait = 2

        def late_reply(command, **kwargs):
            self.clock.now += kwargs['timeout']
            return SimpleNamespace(returncode=0, stdout=b'{"children":[42],"listeners":[17]}', stderr=b'')

        self.run.side_effect = late_reply
        result = instances.start(self.args)
        self.assertEqual('failed', result['state'])
        self.assertEqual(2, self.run.call_args.kwargs['timeout'])
        self.assertEqual(2, self.clock.now)
        self.assertEqual([], self.clock.sleeps)
        self.client.assert_not_called()
        self.assert_retained(result)

    def test_incomplete_discovery_backoff_uses_only_remaining_time(self):
        self.args.wait = 1

        def incomplete_reply(command, **kwargs):
            self.clock.now += .9
            return SimpleNamespace(returncode=0, stdout=b'{"children":[],"listeners":[]}', stderr=b'')

        self.run.side_effect = incomplete_reply
        result = instances.start(self.args)
        self.assertEqual('failed', result['state'])
        self.run.assert_called_once()
        self.assertAlmostEqual(.1, self.clock.sleeps[0])
        self.assertEqual(1, self.clock.now)
        self.client.assert_not_called()
        self.assert_retained(result)

    def test_foreign_listener_still_refuses_binding_without_retry_or_relaunch(self):
        self.run.return_value = SimpleNamespace(returncode=0,
            stdout=b'{"children":[42],"listeners":[99]}', stderr=b'')
        result = instances.start(self.args)
        self.assertEqual('failed', result['state'])
        self.assertIn('refusing to bind', result['error'])
        self.run.assert_called_once()
        self.assertEqual([], self.clock.sleeps)
        self.client.assert_not_called()
        self.assert_retained(result)


if __name__ == '__main__':
    unittest.main()
