"""Manifest reads keep atomic snapshots and distinguish native lock failures."""
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
SPEC = importlib.util.spec_from_file_location('mcdk_read_session',
    ROOT / '.agents/skills/pyreact-debugging/scripts/_session.py')
SESSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SESSION)


def native_error(code):
    error = OSError(13, 'manifest read blocked')
    if code is not None:
        error.winerror = code
    return error


class ManifestReadTests(unittest.TestCase):
    def test_known_conflicts_retry_only_the_read_and_return_fresh_bytes(self):
        for code in (32, 33):
            with self.subTest(winerror=code), \
                    patch.object(SESSION, '_read_manifest_bytes',
                        side_effect=[native_error(code), b'{"version":2}']) as read, \
                    patch.object(SESSION.time, 'sleep') as sleep, \
                    self.assertLogs(SESSION.__name__, level='WARNING') as logs:
                self.assertEqual({'version': 2}, SESSION.read_json('session.json'))
                self.assertEqual(2, read.call_count)
                sleep.assert_called_once_with(.05)
                self.assertIn('winerror=' + str(code), logs.output[0])

    def test_persistent_conflict_has_five_attempts_and_preserves_original_error(self):
        error = native_error(32)
        with patch.object(SESSION, '_read_manifest_bytes', side_effect=error) as read, \
                patch.object(SESSION.time, 'sleep') as sleep, \
                self.assertLogs(SESSION.__name__, level='WARNING'):
            with self.assertRaises(OSError) as caught:
                SESSION.read_json('session.json')
        self.assertIs(error, caught.exception)
        self.assertEqual(5, read.call_count)
        self.assertEqual([.05, .1, .2, .4], [call.args[0] for call in sleep.call_args_list])

    def test_access_denied_unknown_errno_and_other_os_failures_are_not_retried(self):
        for code in (None, 5, 2, 87):
            error = native_error(code)
            with self.subTest(winerror=code), \
                    patch.object(SESSION, '_read_manifest_bytes', side_effect=error) as read, \
                    patch.object(SESSION.time, 'sleep') as sleep:
                with self.assertRaises(OSError) as caught:
                    SESSION.read_json('session.json')
                self.assertIs(error, caught.exception)
                self.assertEqual(1, read.call_count)
                sleep.assert_not_called()

    def test_json_and_utf8_failures_are_not_retried(self):
        for data, expected in ((b'{', json.JSONDecodeError), (b'\xff', UnicodeDecodeError)):
            with self.subTest(data=data), \
                    patch.object(SESSION, '_read_manifest_bytes', return_value=data) as read, \
                    patch.object(SESSION.time, 'sleep') as sleep:
                with self.assertRaises(expected):
                    SESSION.read_json('session.json')
                self.assertEqual(1, read.call_count)
                sleep.assert_not_called()

    def test_session_schema_owner_path_state_and_live_identity_fail_without_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            path = (Path(folder) / 'session.json').resolve()
            path.write_bytes(b'{}')
            good = {'schema': 1, 'session_file': str(path), 'owner': 'assigned',
                'state': 'ready', 'game_pid': 1234, 'game_identity': 'game-old',
                'mcdk_pid': 5678, 'mcdk_identity': 'mcdk-old'}
            cases = [('schema', {'schema': 2}, ValueError),
                ('owner', {'owner': 'another'}, ValueError),
                ('path', {'session_file': str(path.with_name('another.json'))}, ValueError),
                ('state', {'state': 'starting'}, RuntimeError),
                ('identity', {}, RuntimeError)]
            for label, changed, error_type in cases:
                row = dict(good, **changed)
                with self.subTest(label=label), \
                        patch.object(SESSION, '_read_manifest_bytes',
                            return_value=json.dumps(row).encode('utf8')) as read, \
                        patch.object(SESSION, 'process_identity', return_value='reused-pid'), \
                        patch.object(SESSION.time, 'sleep') as sleep:
                    with self.assertRaises(error_type):
                        SESSION.load_session(path, 'assigned', live=True)
                    self.assertEqual(1, read.call_count)
                    sleep.assert_not_called()

    def test_real_utf8_manifest_roundtrip_including_multiple_chunks(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'session.json'
            data = {'owner': '\u51b7\u542f\u52a8', 'payload': '\u6c34\u4e0e\u4e66' * 50000}
            SESSION.write_json(path, data)
            self.assertEqual(data, SESSION.read_json(path))

    @unittest.skipUnless(os.name == 'nt', 'Win32 retained-handle file snapshots')
    def test_renamed_file_keeps_one_complete_old_snapshot_during_path_replacement(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            path = (Path(folder) / 'session.json').resolve()
            before = {'version': 1, 'payload': 'old' * 50000}
            after = {'version': 2, 'payload': 'new' * 50000}
            SESSION.write_json(path, before)
            native = SESSION._manifest_kernel()
            swapped = []

            def read_after_replace(*args):
                if not swapped:
                    # Windows permits renaming the shared-open source. Its
                    # legacy os.replace can still reject an open destination
                    # with code 5; that writer case has its own test below.
                    os.rename(path, path.with_name('retired.json'))
                    SESSION.write_json(path, after)
                    swapped.append(True)
                return native.ReadFile(*args)

            wrapped = SimpleNamespace(CreateFileW=native.CreateFileW,
                ReadFile=read_after_replace, CloseHandle=native.CloseHandle)
            with patch.object(SESSION, '_manifest_kernel', return_value=wrapped):
                self.assertEqual(before, SESSION.read_json(path))
            self.assertEqual([True], swapped)
            self.assertEqual(after, SESSION.read_json(path))

    @unittest.skipUnless(os.name == 'nt', 'Win32 concurrent atomic writer')
    def test_atomic_writer_finishes_after_the_retained_reader_closes(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as folder:
            path = (Path(folder) / 'session.json').resolve()
            before = {'version': 1, 'payload': 'old' * 50000}
            after = {'version': 2, 'payload': 'new' * 50000}
            SESSION.write_json(path, before)
            native = SESSION._manifest_kernel()
            replace = os.replace
            attempts, errors, threads = [], [], []
            first_attempt = threading.Event()

            def observed_replace(source, target):
                try:
                    return replace(source, target)
                finally:
                    attempts.append(True)
                    first_attempt.set()

            def writer():
                try:
                    SESSION.write_json(path, after)
                except Exception as error:
                    errors.append(error)

            def read_with_writer(*args):
                if not threads:
                    thread = threading.Thread(target=writer)
                    threads.append(thread)
                    thread.start()
                    self.assertTrue(first_attempt.wait(3))
                return native.ReadFile(*args)

            wrapped = SimpleNamespace(CreateFileW=native.CreateFileW,
                ReadFile=read_with_writer, CloseHandle=native.CloseHandle)
            try:
                with patch.object(SESSION, '_manifest_kernel', return_value=wrapped), \
                        patch.object(SESSION.os, 'replace', side_effect=observed_replace):
                    self.assertEqual(before, SESSION.read_json(path))
                    threads[0].join(3)
                    self.assertFalse(threads[0].is_alive())
            finally:
                for thread in threads:
                    thread.join(3)
            self.assertFalse(errors, errors)
            self.assertTrue(attempts)
            self.assertEqual(after, SESSION.read_json(path))

    @unittest.skipUnless(os.name == 'nt', 'Win32 sharing and byte-lock conflicts')
    def test_real_native_conflicts_preserve_codes_and_recover_after_release(self):
        from ctypes import wintypes
        native = SESSION._manifest_kernel()
        native.LockFile.argtypes = [wintypes.HANDLE] + [wintypes.DWORD] * 4
        native.LockFile.restype = wintypes.BOOL
        for expected_code in (32, 33):
            with self.subTest(winerror=expected_code), tempfile.TemporaryDirectory() as folder:
                path = (Path(folder) / 'session.json').resolve()
                SESSION.write_json(path, {'complete': True})
                # An incompatible shared open rejects CreateFileW (32). A byte
                # lock permits the open, then rejects ReadFile (33).
                handle = native.CreateFileW(str(path), 0xC0000000,
                    0 if expected_code == 32 else 7, None, 3, 0x80, None)
                self.assertNotIn(handle, (None, ctypes.c_void_p(-1).value))
                if expected_code == 33:
                    self.assertTrue(native.LockFile(handle, 0, 0, 1, 0))
                released = threading.Event()
                timer = None

                def release():
                    native.CloseHandle(handle)
                    released.set()

                try:
                    with self.assertRaises(OSError) as caught:
                        SESSION._read_manifest_bytes(path)
                    self.assertEqual(expected_code, caught.exception.winerror)
                    timer = threading.Timer(.08, release)
                    timer.start()
                    with self.assertLogs(SESSION.__name__, level='WARNING') as logs:
                        self.assertEqual({'complete': True}, SESSION.read_json(path))
                    self.assertTrue(any('winerror=' + str(expected_code) in line for line in logs.output))
                finally:
                    if timer is not None:
                        timer.join()
                    else:
                        release()
                    self.assertTrue(released.is_set())


if __name__ == '__main__':
    unittest.main()
