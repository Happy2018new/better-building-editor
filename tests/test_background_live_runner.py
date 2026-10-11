"""Owner routing and desktop locking remain distinct for SDK-only probes."""
import contextlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import run_live_check as runner


class BackgroundLiveRunnerTests(unittest.TestCase):
    def run_case(self, arguments, **session_changes):
        session = {'project': str(runner.ROOT), 'session_file': 'owned-session.json',
                   'mcp_url': 'http://127.0.0.1:56260/mcp', 'game_pid': 123}
        session.update(session_changes)
        stack = contextlib.ExitStack()
        self.addCleanup(stack.close)
        stack.enter_context(patch.object(sys, 'argv', ['run_live_check.py',
            '--session', 'owned-session.json', '--owner', 'fixture-owner'] + arguments))
        load = stack.enter_context(patch.object(runner, 'load_session', return_value=session))
        lock = stack.enter_context(patch.object(runner, 'desktop_lock'))
        child = stack.enter_context(patch.object(runner.subprocess, 'call', return_value=7))
        return load, lock, child

    def test_sdk_suite_keeps_owner_binding_without_desktop_lock(self):
        load, lock, child = self.run_case(['--sdk-background',
            'verify_dripstone_native_boxes.py', 'evidence.json', '--holdout'])
        with patch.dict(os.environ, {'PYREACT_DESKTOP_LOCK_PID': 'other-owner',
                                    'PYREACT_DESKTOP_LOCK_IDENTITY': 'stale'}):
            self.assertEqual(7, runner.main())
        load.assert_called_once_with('owned-session.json', 'fixture-owner', live=True)
        lock.assert_not_called()
        environment = child.call_args.kwargs['env']
        self.assertEqual('fixture-owner', environment['MCDEV_OWNER'])
        self.assertEqual('owned-session.json', environment['MCDEV_SESSION_FILE'])
        self.assertEqual('123', environment['MCDEV_GAME_PID'])
        self.assertEqual('http://127.0.0.1:56260/mcp', environment['MCDEV_MCP_URL'])
        self.assertNotIn('PYREACT_DESKTOP_LOCK_PID', environment)
        self.assertNotIn('PYREACT_DESKTOP_LOCK_IDENTITY', environment)
        self.assertEqual(['evidence.json', '--holdout'], child.call_args.args[0][-2:])

    def test_unreviewed_suite_cannot_skip_the_desktop_lock(self):
        unused_load, lock, child = self.run_case(['--sdk-background', 'verify_debug_visuals.py'])
        with self.assertRaises(SystemExit) as failure:
            runner.main()
        self.assertEqual(2, failure.exception.code)
        lock.assert_not_called()
        child.assert_not_called()

    def test_other_project_is_rejected_before_child_launch(self):
        unused_load, lock, child = self.run_case(['--sdk-background',
            'verify_dripstone_native_boxes.py'], project=str(runner.ROOT.parent))
        with self.assertRaises(SystemExit) as failure:
            runner.main()
        self.assertEqual(2, failure.exception.code)
        lock.assert_not_called()
        child.assert_not_called()

    def test_default_suite_retains_desktop_ownership(self):
        unused_load, lock, child = self.run_case(['verify_dripstone_native_boxes.py', 'evidence.json'])
        with patch.object(runner, 'process_identity', return_value='parent-identity'):
            self.assertEqual(7, runner.main())
        lock.assert_called_once_with(timeout=30)
        lock.return_value.__enter__.assert_called_once()
        environment = child.call_args.kwargs['env']
        self.assertEqual(str(os.getpid()), environment['PYREACT_DESKTOP_LOCK_PID'])
        self.assertEqual('parent-identity', environment['PYREACT_DESKTOP_LOCK_IDENTITY'])


if __name__ == '__main__':
    unittest.main()
