"""Assertion inspection must not invalidate the session's Windows API types."""
import os
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.name == 'nt', 'Native assertion inspection is a Windows host tool')
class NativeAssertionInspectionTests(unittest.TestCase):
    def test_water_probe_keeps_the_session_rectangle_type(self):
        code = '''import sys
sys.path[:0]=[%r,%r]
import _window
before=_window.user32.GetClientRect.argtypes[1]._type_
assert before is _window.RECT
import probe_product_water
import check_native_dialogs
assert _window.user32.GetClientRect.argtypes[1]._type_ is before
assert check_native_dialogs.capture is _window
windows=_window._list_windows_windows()
assert isinstance(windows,list)
print('native_window_types_preserved')
''' % (str(ROOT / 'tools'), str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
        process = subprocess.run([sys.executable, '-X', 'utf8', '-c', code],
            capture_output=True, text=True, timeout=30, creationflags=subprocess.CREATE_NO_WINDOW)
        self.assertEqual(0, process.returncode, process.stderr)
        self.assertEqual('', process.stderr)
        self.assertIn('native_window_types_preserved', process.stdout)


if __name__ == '__main__':
    unittest.main()
