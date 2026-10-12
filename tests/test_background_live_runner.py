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

    def test_scaffold_segment_retains_range_and_owner_without_desktop_input(self):
        load, lock, child = self.run_case(['--sdk-background',
            'verify_scaffold_support_catalogue.py', 'segment.json', '--start-index', '256', '--count', '256'])
        self.assertEqual(7, runner.main())
        load.assert_called_once_with('owned-session.json', 'fixture-owner', live=True)
        lock.assert_not_called()
        self.assertEqual('fixture-owner', child.call_args.kwargs['env']['MCDEV_OWNER'])
        self.assertEqual(['segment.json', '--start-index', '256', '--count', '256'],
                         child.call_args.args[0][-5:])

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

    def test_native_camera_calibration_skips_lock_but_retains_session(self):
        load, lock, child = self.run_case(['--sdk-background',
            'verify_camera_projection.py', 'evidence.json', '--native-resolution'])
        self.assertEqual(7, runner.main())
        load.assert_called_once_with('owned-session.json', 'fixture-owner', live=True)
        lock.assert_not_called()
        self.assertEqual('fixture-owner', child.call_args.kwargs['env']['MCDEV_OWNER'])

    def test_camera_without_native_background_capture_is_rejected(self):
        unused_load, lock, child = self.run_case(['--sdk-background',
            'verify_camera_projection.py', 'evidence.json'])
        with self.assertRaises(SystemExit):
            runner.main()
        lock.assert_not_called()
        child.assert_not_called()

    def test_background_liquid_capture_requires_reviewed_helper(self):
        helper = str(runner.ROOT / 'tools/verify_sign_visuals.py')
        unused_load, lock, child = self.run_case(['--sdk-background',
            'capture_pure_liquid_native_controls.py', 'evidence.json', '--capture-helper', helper])
        self.assertEqual(7, runner.main())
        lock.assert_not_called()
        self.assertEqual(['--capture-helper', helper], child.call_args.args[0][-2:])

    def test_liquid_capture_cannot_supply_unreviewed_helper(self):
        unused_load, lock, child = self.run_case(['--sdk-background',
            'capture_pure_liquid_native_controls.py', 'evidence.json',
            '--capture-helper', str(runner.ROOT / 'tools/verify_debug_visuals.py')])
        with self.assertRaises(SystemExit):
            runner.main()
        lock.assert_not_called()
        child.assert_not_called()

    def test_frozen_liquid_capture_retains_reviewed_helper_and_owner(self):
        helper = str(runner.ROOT / 'tools/verify_sign_visuals.py')
        load, lock, child = self.run_case(['--sdk-background',
            'capture_frozen_liquid_controls.py', 'evidence.json', '--capture-helper', helper])
        self.assertEqual(7, runner.main())
        load.assert_called_once_with('owned-session.json', 'fixture-owner', live=True)
        lock.assert_not_called()
        self.assertEqual('fixture-owner', child.call_args.kwargs['env']['MCDEV_OWNER'])

    def test_frozen_liquid_capture_rejects_other_helper(self):
        unused_load, lock, child = self.run_case(['--sdk-background',
            'capture_frozen_liquid_controls.py', 'evidence.json',
            '--capture-helper', str(runner.ROOT / 'tools/verify_debug_visuals.py')])
        with self.assertRaises(SystemExit):
            runner.main()
        lock.assert_not_called()
        child.assert_not_called()


if __name__ == '__main__':
    unittest.main()
