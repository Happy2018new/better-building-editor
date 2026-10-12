"""Passive handle counts never cross the owned creation/executable binding."""
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from read_owned_startup_handles import snapshot


class HandleSnapshotTests(unittest.TestCase):
    def kernel(self):
        kernel = Mock()
        kernel.OpenProcess.return_value = 99
        def name(handle, flags, value, size):
            value.value = 'D:/owned/Minecraft.Windows.exe'
            return True
        def count(handle, value):
            value._obj.value = 1234
            return True
        kernel.QueryFullProcessImageNameW.side_effect = name
        kernel.GetProcessHandleCount.side_effect = count
        return kernel

    def test_live_count_has_same_handle_creation_and_executable(self):
        kernel = self.kernel()
        identity = Mock(return_value='owned-creation')
        result = snapshot(kernel, identity, 11, 'owned-creation', 'D:/owned/Minecraft.Windows.exe')
        self.assertEqual(1234, result['handle_count'])
        self.assertEqual('live', result['status'])
        self.assertEqual(2, identity.call_count)
        kernel.CloseHandle.assert_called_once_with(99)

    def test_creation_or_executable_drift_refuses_count(self):
        for creation, executable in (('reused', 'D:/owned/Minecraft.Windows.exe'),
                                     ('owned-creation', 'D:/other/Minecraft.Windows.exe')):
            with self.subTest(creation=creation, executable=executable):
                kernel = self.kernel()
                with self.assertRaises(RuntimeError):
                    snapshot(kernel, Mock(return_value=creation), 11, 'owned-creation', executable)
                kernel.GetProcessHandleCount.assert_not_called()
                kernel.CloseHandle.assert_called_once_with(99)

    def test_dead_process_is_not_a_live_zero_count(self):
        kernel = self.kernel()
        result = snapshot(kernel, Mock(return_value=None), 11, 'owned-creation', 'D:/owned/Minecraft.Windows.exe')
        self.assertEqual('dead', result['status'])
        self.assertNotIn('handle_count', result)
        kernel.GetProcessHandleCount.assert_not_called()

    def test_exit_during_read_is_retained_without_live_claim(self):
        kernel = self.kernel()
        result = snapshot(kernel, Mock(side_effect=['owned-creation', None]),
                          11, 'owned-creation', 'D:/owned/Minecraft.Windows.exe')
        self.assertEqual('exited_during_count', result['status'])
        self.assertEqual(1234, result['handle_count'])


if __name__ == '__main__':
    unittest.main()
