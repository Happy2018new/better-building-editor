"""Background startup fails before spawn when binary or window identity drifts."""
import hashlib
from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances
import _session
import _window as window


def binary(marker):
    return b'MZ' + b'\0' * 58 + (64).to_bytes(4, 'little') + b'PE\0\0\x64\x86' + marker


class GuardContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.dll, self.mcdk = self.folder / 'guard.dll', self.folder / 'mcdk.exe'
        self.dll.write_bytes(binary(b'FocusGuardInitialize\0'))
        self.mcdk.write_bytes(binary('MCDK_NOACTIVATE_DLL'.encode('utf-16le') +
                                    b'Focus guard DLL identity not found in owned process'))
        self.args = SimpleNamespace(mcdk=str(self.mcdk), noactivate_dll=str(self.dll),
            noactivate_sha256=hashlib.sha256(self.dll.read_bytes()).hexdigest(),
            noactivate_mcdk_sha256=hashlib.sha256(self.mcdk.read_bytes()).hexdigest())

    def test_explicit_guard_contract_detaches_paths_and_hashes(self):
        result = instances.noactivate_contract(self.args, self.mcdk)
        self.assertEqual(str(self.dll.resolve()), result['dll']['path'])
        self.assertEqual(self.args.noactivate_mcdk_sha256, result['mcdk']['sha256'])
        self.assertTrue(result['requested'])
        with patch.dict(instances.os.environ, {'MCDK_NOACTIVATE_DLL': 'unapproved.dll',
                                              'MCDEV_SESSION_FILE': 'other.json'}):
            ordinary = instances.clean_environment(self.folder)
            guarded = instances.clean_environment(self.folder, result)
        self.assertNotIn('MCDK_NOACTIVATE_DLL', ordinary)
        self.assertNotIn('MCDEV_SESSION_FILE', guarded)
        self.assertEqual(result['dll']['path'], guarded['MCDK_NOACTIVATE_DLL'])

    def test_guard_options_are_an_explicit_complete_contract(self):
        self.assertIsNone(instances.noactivate_contract(SimpleNamespace(mcdk=None), self.mcdk))
        for field in ('mcdk', 'noactivate_dll', 'noactivate_sha256', 'noactivate_mcdk_sha256'):
            with self.subTest(field=field), patch.object(self.args, field, None):
                with self.assertRaisesRegex(ValueError, 'Noactivation requires'):
                    instances.noactivate_contract(self.args, self.mcdk)

    def test_missing_changed_unpatched_or_wrong_architecture_binaries_are_rejected(self):
        for path, field, source, expected in (
                (self.dll, 'noactivate_sha256', binary(b'changed'), 'SHA256 mismatch'),
                (self.mcdk, 'noactivate_mcdk_sha256', binary(b'official'), 'suspended-child'),
                (self.dll, 'noactivate_sha256', b'not PE', 'Windows x64'),
                (self.dll, 'noactivate_sha256', binary(b'no export'), 'initialization export')):
            with self.subTest(expected=expected):
                original = path.read_bytes()
                path.write_bytes(source)
                supplied = getattr(self.args, field) if expected == 'SHA256 mismatch' else hashlib.sha256(source).hexdigest()
                with patch.object(self.args, field, supplied), self.assertRaisesRegex(ValueError, expected):
                    instances.noactivate_contract(self.args, self.mcdk)
                path.write_bytes(original)
        with patch.object(self.args, 'noactivate_dll', str(self.folder / 'missing.dll')):
            with self.assertRaises(FileNotFoundError):
                instances.noactivate_contract(self.args, self.mcdk)

    def test_hash_failure_stops_start_before_world_preparation_or_subprocess(self):
        self.args.project = str(self.folder)
        self.args.game_exe = 'game.exe'
        with patch.object(instances, 'resolve_mcdk', return_value=str(self.mcdk)), \
             patch.object(instances, 'prepare_world') as prepare, \
             patch.object(instances.subprocess, 'Popen') as spawn, \
             patch.object(self.args, 'noactivate_sha256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                instances.start(self.args)
        prepare.assert_not_called()
        spawn.assert_not_called()

    def test_postpreparation_guard_drift_or_spawn_error_preserves_failed_session(self):
        (self.folder / 'game.exe').write_bytes(b'host game fixture, never executed')
        self.args.project, self.args.game_exe = str(self.folder), 'game.exe'
        self.args.name, self.args.owner = 'host-test', 'host-test'
        self.args.port, self.args.preset, self.args.wait = None, None, 1
        snapshot = {'hwnd': 101, 'pid': 20, 'identity': 'creation', 'process': 'editor.exe'}
        for failure in ('drift', 'spawn'):
            with self.subTest(failure=failure), \
                 patch.object(instances, 'resolve_mcdk', return_value=str(self.mcdk)), \
                 patch.object(instances, 'resolve_game', return_value='game.exe'), \
                 patch.object(instances, 'registry_dir', return_value=self.folder / failure), \
                 patch.object(instances, 'file_lock', return_value=nullcontext()), \
                 patch.object(instances, 'prepare_world', return_value=(self.folder, self.folder)), \
                 patch.object(instances, 'foreground_snapshot', return_value=snapshot), \
                 patch.object(instances, 'validate_foreground_snapshot', return_value=True), \
                 patch.object(instances.subprocess, 'Popen', side_effect=OSError('spawn refused')) as spawn, \
                 patch.object(instances, 'noactivate_contract', side_effect=[{'dll': {}}, ValueError('guard drift')]
                              if failure == 'drift' else [{'dll': {'path': str(self.dll)}}] * 2):
                result = instances.start(self.args)
                self.assertEqual('failed', result['state'])
                self.assertFalse(result['ready'])
                self.assertTrue(result['foreground_unchanged'])
                self.assertEqual('guard drift' if failure == 'drift' else 'spawn refused', result['error'])
                self.assertEqual(0 if failure == 'drift' else 1, spawn.call_count)
                self.assertTrue(Path(result['session_file']).is_file())


class WindowGuardTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = {'hwnd': 101, 'pid': 20, 'identity': 'creation', 'process': 'editor.exe'}

    def test_snapshot_identity_rejects_reused_closed_hidden_or_minimized_windows(self):
        class Native:
            valid, visible, minimized, pid = True, True, False, 20
            def IsWindow(self, hwnd): return self.valid
            def IsWindowVisible(self, hwnd): return self.visible
            def IsIconic(self, hwnd): return self.minimized
            def GetWindowThreadProcessId(self, hwnd, destination): destination._obj.value = self.pid
        native = Native()
        with patch.object(window, 'user32', native), \
             patch.object(window, '_process_name_windows', return_value='editor.exe'), \
             patch.object(_session, 'process_identity', return_value='creation') as identity:
            self.assertTrue(window.validate_foreground_snapshot(self.snapshot))
            for field, value in (('valid', False), ('visible', False), ('minimized', True), ('pid', 21)):
                with self.subTest(field=field), patch.object(native, field, value):
                    self.assertFalse(window.validate_foreground_snapshot(self.snapshot))
            identity.return_value = 'reused PID'
            self.assertFalse(window.validate_foreground_snapshot(self.snapshot))

    def test_guard_state_rejects_any_owned_activating_window_or_game_foreground(self):
        owned = {'hwnd': 101, 'pid': 20, 'process': 'Minecraft.Windows.exe'}
        unrelated = {'hwnd': 201, 'pid': 30, 'process': 'Minecraft.Windows.exe'}
        with patch.object(window, '_list_windows_windows', return_value=[owned, unrelated]), \
             patch.object(window, 'get_window_long', return_value=window.WS_EX_NOACTIVATE) as styles, \
             patch.object(window, 'foreground_snapshot', return_value={'hwnd': 202, 'pid': 30}) as foreground, \
             patch.object(window, '_activate_window') as activate:
            state = window.background_guard_state(20, 'Minecraft.Windows.exe')
            self.assertTrue(state['background_safe'] and state['window_noactivate'])
            styles.assert_called_once_with(101, -20)
            styles.return_value = 0
            self.assertFalse(window.background_guard_state(20, 'Minecraft.Windows.exe')['window_noactivate'])
            foreground.return_value = {'hwnd': 101, 'pid': 20}
            self.assertFalse(window.background_guard_state(20, 'Minecraft.Windows.exe')['background_safe'])
            activate.assert_not_called()

    def test_missing_game_window_is_not_guard_acceptance(self):
        with patch.object(window, '_list_windows_windows', return_value=[]), \
             patch.object(window, 'foreground_snapshot', return_value={'hwnd': 1, 'pid': 2}):
            state = window.background_guard_state(20, 'Minecraft.Windows.exe')
        self.assertFalse(state['window_noactivate'])
        self.assertTrue(state['background_safe'])


if __name__ == '__main__':
    unittest.main()
