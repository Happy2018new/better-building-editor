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
                    stale_session=False, foreground_changed=False):
        directory = Path(temporary)
        executable = directory/'capture.exe'
        executable.write_bytes(b'host-test')
        output = directory/'capture.png'
        session = {'session_file': str(directory/'session.json'), 'owner': 'snow-test',
                   'game_pid': 123, 'game_identity': '456', 'game_executable': 'Minecraft.Windows.exe'}
        window = {'hwnd': 789, 'pid': 123, 'minimized': minimized, 'width': 64, 'height': 48}
        calls = []

        def run(command, **options):
            calls.append((command, options))
            image = Image.new('RGB', (64, 48))
            if not blank:
                image.paste((50, 150, 220), (0, 0, 32, 48))
            image.save(command[-1])
            frame = {'ok': True, 'width': 64, 'height': 48,
                     'request_qpc_100ns': 100, 'frame_qpc_100ns': 99 if stale_frame else 101}
            return type('Result', (), {'returncode': 0, 'stdout': json.dumps(frame), 'stderr': ''})()

        foreground = [{'hwnd': 42, 'pid': 43}, {'hwnd': 44 if foreground_changed else 42, 'pid': 43}]
        with patch.object(capture, 'load_session', side_effect=RuntimeError('Stale instance') if stale_session else None,
                          return_value=session), \
             patch.object(capture, '_list_windows_windows', return_value=[window]), \
             patch.object(capture, '_find_game_window', return_value=window), \
             patch.object(capture, 'foreground', side_effect=foreground), \
             patch.object(capture.subprocess, 'run', side_effect=run):
            rejected = blank or minimized or stale_frame or stale_session or foreground_changed
            if rejected:
                with self.assertRaises(RuntimeError):
                    capture.capture(session['session_file'], session['owner'], output, executable)
            else:
                result = capture.capture(session['session_file'], session['owner'], output, executable)
                self.assertTrue(result['ok'] and result['foreground_unchanged'])
                self.assertEqual((result['width'], result['height']), (64, 48))
        report = json.loads(output.with_suffix('.capture.json').read_text(encoding='utf8'))
        self.assertEqual(report['reliable'], not rejected)
        self.assertEqual(len(calls), 0 if minimized or stale_session else 1)
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
        for case in ('blank', 'minimized', 'stale_frame', 'stale_session', 'foreground_changed'):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                self.run_capture(temporary, **{case: True})


if __name__ == '__main__':
    unittest.main()
