"""Background capture must report unavailable pixels without stealing focus."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_sign_visuals import SignCheck


class BackgroundNativeCaptureTests(unittest.TestCase):
    def run_capture(self, directory, blank, helper=None):
        check = SignCheck.__new__(SignCheck)
        check.output = directory / 'report.json'
        check.native_resolution = check.background_only = True
        check.native_capture_helper = helper
        commands = []
        def capture(command, **kwargs):
            commands.append(command)
            path = Path(command[command.index('--output') + 1])
            image = Image.new('RGB', (16, 16))
            if not blank:
                image.paste((255, 255, 255), (0, 0, 8, 16))
            image.save(path)
            return type('Result', (), {'stdout': json.dumps({'ok': True, 'width': 16, 'height': 16})})()
        with patch('verify_sign_visuals.subprocess.run', capture), \
             patch('verify_sign_visuals.BlueprintCheck.capture', side_effect=AssertionError('Compact capture not allowed')):
            if blank:
                with self.assertRaisesRegex(RuntimeError, 'foreground activation is disabled'):
                    check.capture('water')
            else:
                result = check.capture('water')
                self.assertTrue(result['background_only'])
                self.assertIsNone(result['compact_screenshot'])
        self.assertEqual(len(commands), 1)
        self.assertTrue(commands[0][3].endswith('capture_screen.py') if helper is None else
                        commands[0][3] == str(Path(helper).resolve()))

    def test_black_frame_is_preserved_and_reported_without_activation(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            self.run_capture(directory, True)
            failure = json.loads((directory / 'report_water_native.capture_error.json').read_text(encoding='utf8'))
            self.assertFalse(failure['reliable'])
            self.assertTrue(Path(failure['path']).is_file())

    def test_nonblank_frame_uses_only_target_window_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            self.run_capture(Path(temporary), False)

    def test_explicit_native_helper_replaces_printwindow_without_compact_capture(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            helper = directory/'native_helper.py'
            helper.write_text('', encoding='utf8')
            self.run_capture(directory, False, str(helper))

    def test_repeated_fixture_label_preserves_every_native_frame(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            check = SignCheck.__new__(SignCheck)
            check.output = directory / 'report.json'
            check.native_resolution = check.background_only = True
            check.native_capture_helper = None
            def capture(command, **kwargs):
                path = Path(command[command.index('--output') + 1])
                self.assertFalse(path.exists())
                image = Image.new('RGB', (16, 16))
                image.paste((255, 255, 255), (0, 0, 8, 16))
                image.save(path)
                return type('Result', (), {'stdout': json.dumps({'ok': True})})()
            with patch('verify_sign_visuals.subprocess.run', capture):
                first = check.capture('public_fixture')
                original = Path(first['path']).read_bytes()
                second = check.capture('public_fixture')
            self.assertNotEqual(first['path'], second['path'])
            self.assertEqual(original, Path(first['path']).read_bytes())
            self.assertEqual('public_fixture', second['requested_label'])
            self.assertEqual(2, second['capture_sequence'])


if __name__ == '__main__':
    unittest.main()
