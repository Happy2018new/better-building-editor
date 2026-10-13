"""Physical client measurements restore the caller's thread DPI context."""
import ctypes
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/pyreact-debugging/scripts'))
import _window


class WindowDpiContextTests(unittest.TestCase):
    def test_physical_context_restores_after_normal_and_failed_observation(self):
        for failed in (False, True):
            setter = Mock(side_effect=[123, 456])
            with self.subTest(failed=failed), patch.object(_window, 'user32', Mock(SetThreadDpiAwarenessContext=setter)):
                if failed:
                    with self.assertRaisesRegex(ValueError, 'observation failed'):
                        with _window.physical_window_coordinates():
                            raise ValueError('observation failed')
                else:
                    with _window.physical_window_coordinates():
                        setter.assert_called_once()
                self.assertEqual(ctypes.c_void_p(-4).value, setter.call_args_list[0].args[0].value)
                self.assertEqual(123, setter.call_args_list[1].args[0])

    def test_unavailable_dpi_context_is_not_replaced_with_a_scale_guess(self):
        for setter in (None, Mock(return_value=None)):
            with self.subTest(setter=setter), patch.object(_window, 'user32', Mock(SetThreadDpiAwarenessContext=setter)):
                with self.assertRaises(RuntimeError):
                    with _window.physical_window_coordinates():
                        self.fail('Unavailable physical coordinates cannot qualify')

    def test_failed_restore_is_reported(self):
        with patch.object(_window, 'user32', Mock(SetThreadDpiAwarenessContext=Mock(side_effect=[123, None]))):
            with self.assertRaisesRegex(RuntimeError, 'restore'):
                with _window.physical_window_coordinates():
                    pass


if __name__ == '__main__':
    unittest.main()
