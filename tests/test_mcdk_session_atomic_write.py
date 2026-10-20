"""A temporary Windows reader must not lose a spawned instance's binding."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('mcdk_atomic_session',
    ROOT / '.agents/skills/pyreact-debugging/scripts/_session.py')
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)


def denied(winerror=5):
    error = PermissionError(13, 'Atomic replacement denied')
    if winerror is not None:
        error.winerror = winerror
    return error


class SessionAtomicWriteTests(unittest.TestCase):
    def test_transient_sharing_failure_retries_the_same_complete_write(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session.json'
            path.write_text('{"state":"starting"}', encoding='utf8')
            data = {'state': 'starting', 'mcdk_pid': 12345, 'owner': 'one-instance'}
            replace = os.replace
            attempts = []

            def blocked_then_replace(source, target):
                attempts.append((source, Path(source).read_bytes()))
                if len(attempts) < 3:
                    self.assertEqual(json.loads(path.read_bytes()), {'state': 'starting'})
                    raise denied()
                return replace(source, target)

            with patch.object(SESSION.os, 'replace', side_effect=blocked_then_replace), \
                    patch.object(SESSION.time, 'sleep') as sleep, \
                    self.assertLogs(SESSION.__name__, level='WARNING') as logs:
                SESSION.write_json(path, data)
            self.assertEqual(json.loads(path.read_bytes()), data)
            self.assertEqual(1, len({source for source, raw in attempts}))
            self.assertEqual(1, len({raw for source, raw in attempts}))
            self.assertEqual([(.05,), (.1,)], [call.args for call in sleep.call_args_list])
            self.assertEqual(2, len(logs.output))
            self.assertEqual([], list(Path(folder).glob('*.tmp')))

    def test_bounded_failure_keeps_old_manifest_and_recovery_binding(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session.json'
            old = {'state': 'starting'}
            new = {'state': 'starting', 'mcdk_pid': 12345, 'mcdk_identity': 'creation-id'}
            path.write_text(json.dumps(old), encoding='utf8')
            error = denied(32)
            with patch.object(SESSION.os, 'replace', side_effect=error) as replace, \
                    patch.object(SESSION.time, 'sleep') as sleep, \
                    self.assertLogs(SESSION.__name__, level='WARNING'):
                with self.assertRaises(PermissionError) as caught:
                    SESSION.write_json(path, new)
            self.assertIs(error, caught.exception)
            self.assertEqual(5, replace.call_count)
            self.assertEqual([(.05,), (.1,), (.2,), (.4,)],
                             [call.args for call in sleep.call_args_list])
            self.assertEqual(json.loads(path.read_bytes()), old)
            leftovers = list(Path(folder).glob('*.tmp'))
            self.assertEqual(1, len(leftovers))
            self.assertEqual(json.loads(leftovers[0].read_bytes()), new)

    def test_unrelated_permission_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as folder:
            error = denied(None)
            with patch.object(SESSION.os, 'replace', side_effect=error) as replace, \
                    patch.object(SESSION.time, 'sleep') as sleep:
                with self.assertRaises(PermissionError) as caught:
                    SESSION.write_json(Path(folder) / 'session.json', {'mcdk_pid': 12345})
            self.assertIs(error, caught.exception)
            self.assertEqual(1, replace.call_count)
            sleep.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_actual_windows_reader_without_share_delete_can_release_during_retry(self):
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session.json'
            path.write_text('{"state":"starting"}', encoding='utf8')
            # GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, OPEN_EXISTING.
            handle = kernel.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
            self.assertNotEqual(ctypes.c_void_p(-1).value, handle)
            self.assertIsNotNone(handle)
            released = threading.Event()

            def release():
                kernel.CloseHandle(handle)
                released.set()

            timer = threading.Timer(.08, release)
            timer.start()
            try:
                with self.assertLogs(SESSION.__name__, level='WARNING'):
                    SESSION.write_json(path, {'state': 'starting', 'mcdk_pid': 12345})
                self.assertEqual(12345, json.loads(path.read_bytes())['mcdk_pid'])
            finally:
                timer.join()
                self.assertTrue(released.is_set())


if __name__ == '__main__':
    unittest.main()
