"""WGC evidence rejects stale identity, old frames and unusable pixels."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import capture_native_window as capture


class NativeCaptureTests(unittest.TestCase):
    def run_capture(self, temporary, *, blank=False, minimized=False, stale_frame=False,
                    stale_session=False, foreground_changed=False,
                    game_foreground_before=False, game_foreground_after=False,
                    allow_foreground=False, lost_style=False, changed_identity=False,
                    unprotected=False, changed_size=False):
        directory = Path(temporary)
        executable = directory/'capture.exe'
        executable.write_bytes(b'host-test')
        output = directory/'capture.png'
        session = {'session_file': str(directory/'session.json'), 'owner': 'snow-test',
                   'game_pid': 123, 'game_identity': '456', 'game_executable': 'Minecraft.Windows.exe',
                   'noactivation': {'requested': True, 'window_noactivate': True}}
        if unprotected:
            session['noactivation'] = {}
        window = {'hwnd': 789, 'pid': 123, 'minimized': minimized, 'width': 64, 'height': 48,
                  'noactivate': not lost_style}
        calls = []

        def run(command, **options):
            calls.append((command, options))
            image = Image.new('RGB', (64, 48))
            if not blank:
                image.paste((50, 150, 220), (0, 0, 32, 48))
            image.save(command[-1])
            frame = {'ok': True, 'width': 65 if changed_size else 64, 'height': 48,
                     'request_qpc_100ns': 100, 'frame_qpc_100ns': 99 if stale_frame else 101}
            return type('Result', (), {'returncode': 0, 'stdout': json.dumps(frame), 'stderr': ''})()

        foreground = [{'hwnd': 42, 'pid': 43}, {'hwnd': 44 if foreground_changed else 42, 'pid': 43}]
        if game_foreground_before:
            foreground[0] = {'hwnd': 789, 'pid': 123}
        if game_foreground_after:
            foreground[1] = {'hwnd': 789, 'pid': 123}
        guards = [{'foreground': value, 'windows': [window], 'window_noactivate': not lost_style,
                   'background_safe': value['pid'] != 123} for value in foreground]
        session_values = [session, dict(session, game_identity='changed')] if changed_identity else [session, session]
        with patch.object(capture, 'load_session', side_effect=RuntimeError('Stale instance') if stale_session else None,
                          return_value=session), \
             patch.object(capture, '_list_windows_windows', return_value=[window]), \
             patch.object(capture, '_find_game_window', return_value=window), \
             patch.object(capture, 'foreground', side_effect=foreground), \
             patch.object(capture, 'background_guard_state', side_effect=guards), \
             patch.dict(capture.os.environ, {'MCDEV_ALLOW_USER_FOREGROUND': '1' if allow_foreground else '0'}), \
             patch.object(capture.subprocess, 'run', side_effect=run):
            if changed_identity:
                capture.load_session.side_effect = session_values
            rejected = (blank or minimized or stale_frame or stale_session or changed_identity or
                        unprotected or changed_size or
                        lost_style or (not allow_foreground and (game_foreground_before or game_foreground_after)))
            if rejected:
                with self.assertRaises(RuntimeError):
                    capture.capture(session['session_file'], session['owner'], output, executable)
            else:
                result = capture.capture(session['session_file'], session['owner'], output, executable)
                self.assertTrue(result['ok'])
                self.assertEqual(result['background_safe'], not game_foreground_after)
                self.assertEqual(result['foreground_unchanged'], foreground[0] == foreground[1])
                self.assertEqual((result['width'], result['height']), (64, 48))
        report = json.loads(output.with_suffix('.capture.json').read_text(encoding='utf8'))
        self.assertEqual(report['reliable'], not rejected)
        self.assertEqual(len(calls), 0 if minimized or stale_session or lost_style or unprotected or
                         (game_foreground_before and not allow_foreground) else 1)
        if allow_foreground and not rejected:
            self.assertEqual(3, report['schema'])
            self.assertEqual('allow_user_foreground', report['foreground_policy'])
            self.assertTrue(report['user_foreground_allowed'] and report['noactivation_requested'])
            self.assertFalse(report['agent_activation_allowed'] or report['activation_fallback'])
            self.assertEqual(guards[0], report['guard_before'])
            self.assertEqual(guards[1], report['guard_after'])
        if calls:
            self.assertEqual(calls[0][0][1:4], ['789', '123', '456'])
            self.assertEqual(calls[0][1]['creationflags'], capture.subprocess.CREATE_NO_WINDOW)
        if blank:
            self.assertTrue(output.is_file())
            self.assertIn('blank', report['error'])

    def test_current_nonblank_native_frame_preserves_binding_and_foreground(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.run_capture(temporary)

    def test_rejections_keep_diagnostics_and_do_not_activate(self):
        for case in ('blank', 'minimized', 'stale_frame', 'stale_session',
                     'game_foreground_before', 'game_foreground_after'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                self.run_capture(temporary, **{case: True})

    def test_switching_other_applications_preserves_accurate_background_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.run_capture(temporary, foreground_changed=True)

    def test_opt_in_accepts_user_observation_and_foreground_transitions(self):
        for before, after in ((True, True), (True, False), (False, True), (False, False)):
            with self.subTest(before=before, after=after), tempfile.TemporaryDirectory() as temporary:
                self.run_capture(temporary, allow_foreground=True,
                                 game_foreground_before=before, game_foreground_after=after)

    def test_opt_in_does_not_accept_stale_blank_or_unprotected_frames(self):
        for fault in ('blank', 'minimized', 'stale_frame', 'stale_session', 'lost_style', 'changed_identity',
                      'unprotected', 'changed_size'):
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                self.run_capture(temporary, allow_foreground=True, game_foreground_before=True,
                                 game_foreground_after=True, **{fault: True})


if __name__ == '__main__':
    unittest.main()
