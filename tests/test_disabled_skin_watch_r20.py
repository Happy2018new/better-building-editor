"""The unattended recovery must reject other dialogs and unrelated processes."""
import ctypes
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from dismiss_owned_disabled_skin_assert import known_disabled_skin_assertion, post_owned_ignore
from watch_owned_disabled_skin_assert_r20 import assigned, eligible
import watch_owned_disabled_skin_assert_r20 as watcher


class IgnoreDialog:
    """Small Win32 boundary fake; a posted message is the only mutation."""
    def __init__(self):
        self.pids = {100: 11, 200: 11}
        self.classes = {100: '#32770', 200: 'Button'}
        self.parent = 100
        self.control_id = 5
        self.button = 200
        self.button_text = '\u5ffd\u7565(&I)'
        self.hidden = set()
        self.posted = []

    def GetWindowThreadProcessId(self, window, pid):
        pid._obj.value = self.pids.get(window, 0)
        return 1

    def GetDlgItem(self, window, control):
        return self.button if window == 100 and control == 5 else 0

    def GetDlgCtrlID(self, window):
        return self.control_id

    def GetParent(self, window):
        return self.parent

    def GetClassNameW(self, window, buffer, size):
        buffer.value = self.classes.get(window, '')
        return len(buffer.value)

    def GetWindowTextW(self, window, buffer, size):
        buffer.value = self.button_text
        return len(buffer.value)

    def IsWindowVisible(self, window):
        return window not in self.hidden

    def PostMessageW(self, *message):
        self.posted.append(message)
        return True


class DisabledSkinWatchTests(unittest.TestCase):
    def owned_dialog(self):
        return {'pid': 11, 'hwnd': 100, 'text': (
            'The disabled skin popup has been displayed but the level data has no disabled cosmetics\n'
            'DisabledSkinScreenController::onEntered(void)\nDisabledSkinScreenController.cpp @ 47')}

    def click(self, native, row=None, save=None, identity=None, dialogs=None):
        row = row or self.owned_dialog()
        return post_owned_ignore({'game_pid': 11, 'game_identity': 'game-a'}, row,
                                 save or (lambda target: None), user=native,
                                 identity_reader=identity or (lambda pid: 'game-a'),
                                 dialog_reader=dialogs or (lambda: [row]))

    def test_posts_to_verified_ignore_button_5_after_persisting_target_without_activation(self):
        for label in ('\u5ffd\u7565(&I)', '&Ignore'):
            with self.subTest(label=label):
                native = IgnoreDialog()
                native.button_text = label
                saved = []
                def save(target):
                    self.assertEqual([], native.posted)
                    saved.append(target)
                target = self.click(native, save=save)
                self.assertEqual([(200, 0x00F5, 0, 0)], native.posted)
                self.assertEqual([target], saved)
                self.assertEqual(5, target['control_id'])
                self.assertFalse(target['agent_activation'])

    def test_refuses_wrong_process_parent_class_control_label_and_hidden_targets_without_click(self):
        mutations = (
            lambda api: api.pids.update({100: 99}),
            lambda api: api.pids.update({200: 99}),
            lambda api: setattr(api, 'parent', 999),
            lambda api: setattr(api, 'control_id', 7),
            lambda api: setattr(api, 'button', 0),
            lambda api: api.classes.update({100: 'UnrelatedDialog'}),
            lambda api: api.classes.update({200: 'Static'}),
            lambda api: setattr(api, 'button_text', '&Retry'),
            lambda api: api.hidden.add(100),
            lambda api: api.hidden.add(200),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                native = IgnoreDialog()
                mutate(native)
                with self.assertRaises(RuntimeError):
                    self.click(native)
                self.assertEqual([], native.posted)

    def test_refuses_unknown_changed_multiple_or_disappeared_assertions_without_click(self):
        row = self.owned_dialog()
        for rows in ([], [dict(row, hwnd=999)], [dict(row, text='another failure')],
                     [row, dict(row, hwnd=999)]):
            with self.subTest(rows=rows):
                native = IgnoreDialog()
                with self.assertRaises(RuntimeError):
                    self.click(native, dialogs=lambda: rows)
                self.assertEqual([], native.posted)
        native = IgnoreDialog()
        with self.assertRaises(ValueError):
            self.click(native, row=dict(row, text='another failure'))
        self.assertEqual([], native.posted)

    def test_revalidates_process_and_button_after_receipt_io(self):
        native = IgnoreDialog()
        identities = iter(('game-a', 'reused-process'))
        with self.assertRaises(RuntimeError):
            self.click(native, identity=lambda pid: next(identities))
        self.assertEqual([], native.posted)
        native = IgnoreDialog()
        with self.assertRaises(RuntimeError):
            self.click(native, save=lambda target: setattr(native, 'button', 999))
        self.assertEqual([], native.posted)

    def test_rechecks_dialog_text_class_and_visibility_after_receipt_io(self):
        for change in ('text', 'class', 'hidden', 'label'):
            with self.subTest(change=change):
                native = IgnoreDialog()
                row = self.owned_dialog()
                def save(target):
                    if change == 'text':
                        row['text'] = 'A different engine assertion'
                    elif change == 'class':
                        native.classes[100] = 'OtherDialog'
                    elif change == 'hidden':
                        native.hidden.add(200)
                    else:
                        native.button_text = '&Retry'
                with self.assertRaises(RuntimeError):
                    self.click(native, row=row, save=save)
                self.assertEqual([], native.posted)

    def test_refuses_process_identity_changed_during_receipt_io_without_click(self):
        native = IgnoreDialog()
        identity = {'value': 'game-a'}
        saved = []

        def save(target):
            self.assertEqual([], native.posted)
            saved.append(target)
            identity['value'] = 'reused-process'

        with self.assertRaisesRegex(RuntimeError, 'Game process identity changed'):
            self.click(native, save=save, identity=lambda pid: identity['value'])
        self.assertEqual(1, len(saved))
        self.assertEqual(5, saved[0]['control_id'])
        self.assertEqual([], native.posted)

    def test_only_explicit_assignment_prefixes_extend_to_next_cold_instance(self):
        self.assertTrue(assigned('portal-r20-native-v4', ['portal-r20-native-*']))
        self.assertFalse(assigned('user-game', ['portal-r20-native-*']))
        self.assertFalse(assigned('portal-r19-native-v4', ['portal-r20-native-*']))
        self.assertFalse(assigned('user-game', ['*']))
        self.assertFalse(assigned(None, ['portal-r20-native-*']))

    def test_only_the_specific_engine_assertion_matches(self):
        text = ('The disabled skin popup has been displayed but the level data has no disabled cosmetics\n'
                'DisabledSkinScreenController::onEntered(void)\nDisabledSkinScreenController.cpp @ 47')
        self.assertTrue(known_disabled_skin_assertion({'text': text}))
        self.assertFalse(known_disabled_skin_assertion({'text': text.replace('@ 47', '@ 48')}))
        self.assertFalse(known_disabled_skin_assertion({'text': text.replace('no disabled', 'disabled')}))
        self.assertFalse(known_disabled_skin_assertion({'text': 'Assertion failed in another renderer'}))

    def test_only_explicitly_owned_live_project_instances_are_eligible(self):
        project_root = (ROOT / '.runtime/projects').resolve()
        record = {'owner': 'shield-r20-v1', 'state': 'starting',
                  'project': str(project_root / 'shield-r20-v1'),
                  'game_pid': 11, 'game_identity': 'game-a', 'mcdk_pid': 12, 'mcdk_identity': 'mcdk-a'}
        identities = {11: 'game-a', 12: 'mcdk-a'}
        check = lambda item: eligible(item, ['shield-r20-v1'], project_root, identities.get)
        self.assertTrue(check(record))
        for change in ({'owner': 'user-game'}, {'state': 'stopped'},
                       {'project': str(ROOT)}, {'project': str(project_root) + '-other/clone'},
                       {'game_identity': 'game-reused'}, {'mcdk_identity': 'old-mcdk'},
                       {'game_pid': None}):
            self.assertFalse(check(dict(record, **change)), change)

    @unittest.skipUnless(os.name == 'nt', 'Actual Windows manifest sharing conflict')
    def test_once_watch_reads_a_temporarily_locked_registry_and_publishes_complete_status(self):
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as folder:
            registry = Path(folder) / 'registry'
            manifest = registry / 'unrelated' / 'session.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"owner":"unrelated-user"}', encoding='utf8')
            output = Path(folder) / 'watch'
            handle = kernel.CreateFileW(str(manifest), 0x80000000, 0, None, 3, 0, None)
            self.assertNotIn(handle, (None, ctypes.c_void_p(-1).value))
            released = threading.Event()

            def release():
                kernel.CloseHandle(handle)
                released.set()

            timer = threading.Timer(.08, release)
            timer.start()
            replacements = []
            real_replace = os.replace

            def observe_publish(source, target):
                self.assertEqual(output / 'status.json', target)
                self.assertFalse(target.exists())
                value = json.loads(Path(source).read_bytes())
                self.assertEqual(['test-owner'], value['owners'])
                self.assertEqual([], value['errors'])
                self.assertIn('checked_at', value)
                replacements.append(value)
                return real_replace(source, target)

            until = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
            arguments = ['watcher', '--owner', 'test-owner', '--until', until,
                         '--output', str(output), '--once']
            try:
                with patch.object(sys, 'argv', arguments), \
                        patch.object(watcher, 'registry_dir', return_value=registry), \
                        patch.object(watcher, 'assertion_dialogs', return_value=[]), \
                        patch.object(watcher, 'load_session') as load, \
                        patch.object(os, 'replace', side_effect=observe_publish), \
                        self.assertLogs('_session', level='WARNING'):
                    self.assertEqual(0, watcher.main())
                load.assert_not_called()
                self.assertEqual(1, len(replacements))
                self.assertEqual(replacements[0], watcher.read_json(output / 'status.json'))
                self.assertEqual([], list(output.glob('*.tmp')))
            finally:
                timer.join()
                self.assertTrue(released.is_set())

    def test_once_watch_preserves_malformed_manifest_as_a_recorded_error(self):
        with tempfile.TemporaryDirectory() as folder:
            registry = Path(folder) / 'registry'
            manifest = registry / 'broken' / 'session.json'
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"owner":', encoding='utf8')
            output = Path(folder) / 'watch'
            until = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
            arguments = ['watcher', '--owner', 'test-owner', '--until', until,
                         '--output', str(output), '--once']
            with patch.object(sys, 'argv', arguments), \
                    patch.object(watcher, 'registry_dir', return_value=registry), \
                    patch.object(watcher, 'assertion_dialogs', return_value=[]), \
                    patch.object(watcher, 'load_session') as load:
                self.assertEqual(1, watcher.main())
            load.assert_not_called()
            status = watcher.read_json(output / 'status.json')
            self.assertEqual(1, len(status['errors']))
            self.assertIn(str(manifest), status['errors'][0])
            self.assertEqual([], status['eligible_sessions'])


if __name__ == '__main__':
    unittest.main()
