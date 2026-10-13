"""World admission keeps air None, but never admits missing nonair states."""
import copy
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import run_scaffold_runtime_lifecycle as runner


class RuntimeAdmissionTests(unittest.TestCase):
    def sample(self):
        client = {'runtime': runner.world.RUNTIME, 'ui_initialized': True, 'render_ticks': 2,
                  'player': 'player', 'foot': [.5, -60., .5]}
        server = {'runtime': runner.world.RUNTIME, 'player': 'player', 'foot': [.5, -60., .5],
                  'dimension': 0, 'ground': {'front': {'name': 'minecraft:grass_block', 'aux': 0}, 'states': {}},
                  'reserve': [{'offset': offset, 'front': {'name': 'minecraft:air', 'aux': 0},
                               'states': None, 'liquid': None} for offset in runner.world.OFFSETS]}
        return client, server

    def test_air_none_is_admitted_but_never_changed(self):
        client, server = self.sample()
        before = copy.deepcopy(server)
        self.assertTrue(runner.physical_ready(client, server))
        self.assertEqual(before, server)
        self.assertTrue(all(row['states'] is None for row in server['reserve']))

    def test_ui_loading_identity_and_nonair_state_failures_are_rejected(self):
        for change in ('ui', 'ticks', 'height', 'dimension', 'player', 'ground', 'nonair', 'wet'):
            client, server = self.sample()
            if change == 'ui':
                client['ui_initialized'] = False
            elif change == 'ticks':
                client['render_ticks'] = 1
            elif change == 'height':
                server['foot'][1] = client['foot'][1] = 32769.6
            elif change == 'dimension':
                server['dimension'] = False
            elif change == 'player':
                server['player'] = 'another-player'
            elif change == 'ground':
                server['ground']['states'] = None
            elif change == 'nonair':
                server['reserve'][0]['front']['name'] = 'minecraft:stone'
            else:
                server['reserve'][0]['liquid'] = {'name': 'minecraft:water', 'aux': 0}
            with self.subTest(change=change):
                self.assertFalse(runner.physical_ready(client, server))


class SourceArchiveTests(unittest.TestCase):
    def test_exact_bytes_are_retained_after_source_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            source = root / 'tools' / 'probe.py'
            source.parent.mkdir(parents=True)
            raw = b'# frozen source\r\nvalue = "\xe6\xb0\xb4"\r\n'
            source.write_bytes(raw)
            output = Path(directory) / 'output'
            source_pins, archive_pins = runner.archive_sources(root, output, [source])
            expected = hashlib.sha256(raw).hexdigest()
            self.assertEqual(source_pins, {str(source.resolve()): expected})
            self.assertEqual(list(archive_pins.values()), [expected])
            archived = output / next(iter(archive_pins))
            source.write_bytes(b'changed')
            self.assertEqual(archived.read_bytes(), raw)
            self.assertEqual(runner.digest(archived), expected)
            self.assertNotEqual(runner.digest(source), expected)

    def test_source_outside_owned_root_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            root.mkdir()
            source = Path(directory) / 'other.py'
            source.write_bytes(b'outside')
            with self.assertRaises(ValueError):
                runner.archive_sources(root, Path(directory) / 'output', [source])


class UserForegroundTests(unittest.TestCase):
    def guard(self, foreground_pid=42):
        return {'foreground': {'pid': foreground_pid}, 'background_safe': foreground_pid != 42,
                'windows': [{'pid': 42, 'noactivate': True}], 'window_noactivate': True}

    def test_user_foreground_continues_with_explicit_environment_permission(self):
        for permitted in ('', '0', 'true', '1'):
            with self.subTest(permitted=permitted), patch.dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND=permitted):
                self.assertEqual(runner.scaffold_guard_satisfied(self.guard(), 42), permitted == '1')
                self.assertEqual(runner.scaffold_guard_satisfied(self.guard(), 42, require_window=True), permitted == '1')
                self.assertTrue(runner.scaffold_guard_satisfied(self.guard(43), 42))
                metadata = runner.foreground_metadata()
                self.assertEqual(metadata['user_foreground_allowed'], permitted == '1')
                self.assertEqual(metadata['background_only'], permitted != '1')
                self.assertIs(metadata['agent_activation_allowed'], False)
                self.assertIs(metadata['activation_fallback'], False)

    def test_foreground_permission_does_not_hide_false_receipts_or_missing_guard(self):
        with patch.dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND='1'):
            for change in ('background_claim', 'guard_lost', 'guard_int', 'pid_bool', 'pid_missing'):
                guard = self.guard()
                if change == 'background_claim':
                    guard['background_safe'] = True
                elif change == 'guard_lost':
                    guard['window_noactivate'] = False
                elif change == 'guard_int':
                    guard['window_noactivate'] = 1
                elif change == 'pid_bool':
                    guard['foreground']['pid'] = True
                else:
                    guard['foreground'].pop('pid')
                with self.subTest(change=change):
                    self.assertFalse(runner.scaffold_guard_satisfied(guard, 42))
            guard = self.guard()
            guard['windows'] = []
            self.assertTrue(runner.scaffold_guard_satisfied(guard, 42))
            self.assertFalse(runner.scaffold_guard_satisfied(guard, 42, require_window=True))

    def test_existing_minecraft_foreground_is_allowed_only_by_the_user_policy(self):
        for allowed in ('0', '1'):
            with patch.dict(os.environ, MCDEV_ALLOW_USER_FOREGROUND=allowed):
                self.assertEqual(runner.startup_foreground_satisfied({'process': 'Minecraft.Windows.exe'}), allowed == '1')
                self.assertTrue(runner.startup_foreground_satisfied({'process': 'Code.exe'}))


if __name__ == '__main__':
    unittest.main()
