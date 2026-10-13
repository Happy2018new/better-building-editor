"""Bounded filesystem retries must not weaken startup session ownership."""
import errno
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import managed_registry_snapshot as registry


class RegistrySnapshotTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.path = self.root / 'owned/session.json'
        self.path.parent.mkdir()
        self.row = {'schema': 1, 'owner': 'owner', 'project': str(self.root),
                    'session_file': str(self.path), 'state': 'starting'}
        self.path.write_text(json.dumps(self.row), encoding='ascii')

    def find(self, **kwargs):
        return registry.find_owner_session(self.root, 'owner', self.root, **kwargs)

    def test_current_snapshot_is_returned_without_a_retry(self):
        callback = mock.Mock()
        self.assertEqual(self.row, self.find(on_retry=callback))
        callback.assert_not_called()

    def test_transient_permission_error_retries_read_only_and_records_stage(self):
        callback = mock.Mock()
        denied = PermissionError(errno.EACCES, 'Sharing conflict')
        with mock.patch.object(Path, 'read_bytes', side_effect=[denied, json.dumps(self.row).encode('ascii')]) as read:
            self.assertEqual(self.row, self.find(on_retry=callback))
        self.assertEqual(read.call_count, 2)
        self.assertEqual(callback.call_args.args[0],
                         {'stage': 'read_session_manifest', 'manifest_id': 'owned',
                          'attempt': 1, 'errno': errno.EACCES, 'winerror': None})

    def test_persistent_permission_error_stops_at_deadline(self):
        denied = PermissionError(errno.EACCES, 'Persistent denial')
        with mock.patch.object(Path, 'read_bytes', side_effect=denied) as read:
            with mock.patch.object(registry.time, 'monotonic', side_effect=[0, .6, 1.1]):
                with mock.patch.object(registry.time, 'sleep') as sleep:
                    with self.assertRaises(PermissionError):
                        self.find(timeout=1)
        self.assertEqual(read.call_count, 2)
        sleep.assert_called_once_with(.05)

    def test_guard_failure_in_retry_callback_is_not_swallowed(self):
        with mock.patch.object(Path, 'read_bytes', side_effect=PermissionError(errno.EACCES, 'Denied')):
            with self.assertRaisesRegex(RuntimeError, 'Identity changed'):
                self.find(on_retry=mock.Mock(side_effect=RuntimeError('Identity changed')))

    def test_invalid_json_missing_file_and_other_io_errors_are_not_retried(self):
        for failure in (json.JSONDecodeError('Invalid', '', 0),
                        FileNotFoundError(errno.ENOENT, 'Missing'), OSError(errno.EIO, 'IO')):
            with self.subTest(failure=type(failure).__name__):
                callback = mock.Mock()
                with mock.patch.object(Path, 'read_bytes', side_effect=failure) as read:
                    with self.assertRaises(type(failure)):
                        self.find(on_retry=callback)
                self.assertEqual(read.call_count, 1)
                callback.assert_not_called()

    def test_owner_and_project_do_not_match_by_basename(self):
        self.assertIsNone(registry.find_owner_session(self.root, 'other', self.root))
        self.assertIsNone(registry.find_owner_session(self.root, 'owner', self.root / 'other'))

    def test_schema_and_manifest_path_are_validated(self):
        for field, value in (('schema', 2), ('session_file', str(self.root / 'other/session.json'))):
            with self.subTest(field=field):
                row = dict(self.row, **{field: value})
                self.path.write_text(json.dumps(row), encoding='ascii')
                with self.assertRaisesRegex(ValueError, 'Invalid owner-bound'):
                    self.find()

    def test_multiple_matching_sessions_are_refused(self):
        other = self.root / 'duplicate/session.json'
        other.parent.mkdir()
        other.write_text(json.dumps(dict(self.row, session_file=str(other))), encoding='ascii')
        with self.assertRaisesRegex(RuntimeError, 'Ambiguous'):
            self.find()

    def test_one_deadline_covers_every_manifest(self):
        other = self.root / 'zz-other/session.json'
        other.parent.mkdir()
        other.write_text(json.dumps(dict(self.row, owner='another', session_file=str(other))), encoding='ascii')
        with mock.patch.object(Path, 'read_bytes', side_effect=[self.path.read_bytes(), PermissionError(13, 'Denied')]) as read:
            with mock.patch.object(registry.time, 'monotonic', side_effect=[0, 1.1]):
                with self.assertRaises(PermissionError):
                    self.find(timeout=1)
        self.assertEqual(read.call_count, 2)

    def test_unbounded_timeout_is_refused_before_reading(self):
        for timeout in (0, -1, 3, True, float('inf')):
            with self.subTest(timeout=timeout):
                with self.assertRaises(ValueError):
                    self.find(timeout=timeout)


if __name__ == '__main__':
    unittest.main()
