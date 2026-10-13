"""Explicit user foreground permission cannot waive capture identity or guards."""
from copy import deepcopy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_liquid_workspace import capture_failures


class UserForegroundCaptureContractTests(unittest.TestCase):
    def receipt(self, directory, before_owned=False, after_owned=False):
        path = Path(directory) / 'frame.png'
        image = Image.new('RGB', (8, 8), (30, 40, 50))
        image.putpixel((0, 0), (200, 200, 200))
        image.save(path)
        binding = {'owner': 'owned', 'game_pid': 9, 'game_identity': '123', 'session_file': 'session.json'}
        window = {'hwnd': 99, 'pid': 9, 'width': 8, 'height': 8, 'minimized': False, 'noactivate': True}
        row = dict(binding, schema=3, ok=True, reliable=True, native_resolution=True,
                   foreground_policy='allow_user_foreground', user_foreground_allowed=True,
                   agent_activation_allowed=False, activation_fallback=False,
                   noactivation_requested=True, guarded_no_activation=True, background_only=False,
                   window=deepcopy(window), backend='Windows.Graphics.Capture', variance=[30., 30., 30.],
                   width=8, height=8, path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                   frame={'backend': 'Windows.Graphics.Capture', 'request_qpc_100ns': 100, 'frame_qpc_100ns': 101})
        for phase, owned in (('before', before_owned), ('after', after_owned)):
            foreground = {'hwnd': 99 if owned else 22, 'pid': 9 if owned else 2}
            row['foreground_' + phase] = foreground
            row['guard_' + phase] = {'foreground': deepcopy(foreground), 'windows': [deepcopy(window)],
                                    'window_noactivate': True, 'background_safe': not owned}
        row['background_safe'] = not after_owned
        row['foreground_unchanged'] = before_owned == after_owned
        return binding, row

    def assert_rejected(self, binding, row):
        self.assertTrue(capture_failures({'frame': row}, binding))

    def test_explicit_permission_accepts_stable_and_changing_user_foreground(self):
        with tempfile.TemporaryDirectory() as directory:
            for before in (False, True):
                for after in (False, True):
                    with self.subTest(before=before, after=after):
                        binding, row = self.receipt(directory, before, after)
                        self.assertEqual([], capture_failures({'frame': row}, binding))

    def test_guard_snapshots_can_retain_richer_foreground_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, row = self.receipt(directory, False, True)
            for phase in ('before', 'after'):
                row['guard_' + phase]['foreground'].update(identity='123', title='Game', visible=True)
            self.assertEqual([], capture_failures({'frame': row}, binding))
            row['guard_before']['foreground']['pid'] = 3
            self.assert_rejected(binding, row)

    def test_policy_flags_require_explicit_exact_values(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, original = self.receipt(directory, True, True)
            fields = ('foreground_policy', 'user_foreground_allowed', 'agent_activation_allowed',
                      'activation_fallback', 'noactivation_requested', 'guarded_no_activation',
                      'background_only', 'schema')
            for key in fields:
                for value in (None, 'true', 1):
                    with self.subTest(key=key, value=value):
                        row = deepcopy(original)
                        row[key] = value
                        self.assert_rejected(binding, row)
                row = deepcopy(original)
                del row[key]
                self.assert_rejected(binding, row)
            for value in (2, 3., True, 4):
                row = dict(original, schema=value)
                self.assert_rejected(binding, row)

    def test_foreground_snapshots_must_match_guards_and_actual_background_flags(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, original = self.receipt(directory, False, True)
            for phase in ('before', 'after'):
                for key, value in (('pid', None), ('pid', '9'), ('pid', True), ('pid', -1),
                                   ('hwnd', None), ('hwnd', -1), ('hwnd', 0), ('hwnd', '99')):
                    row = deepcopy(original)
                    row['foreground_' + phase][key] = value
                    with self.subTest(phase=phase, key=key, value=value):
                        self.assert_rejected(binding, row)
                row = deepcopy(original)
                row['guard_' + phase]['background_safe'] = phase == 'after'
                self.assert_rejected(binding, row)
                row = deepcopy(original)
                row['guard_' + phase]['background_safe'] = int(row['guard_' + phase]['background_safe'])
                self.assert_rejected(binding, row)
                for key in ('guard_' + phase, 'foreground_' + phase):
                    row = deepcopy(original)
                    del row[key]
                    self.assert_rejected(binding, row)
            for field, value in (('background_safe', True), ('background_safe', 0),
                                 ('foreground_unchanged', True), ('foreground_unchanged', 0)):
                row = dict(original, **{field: value})
                self.assert_rejected(binding, row)
            row = deepcopy(original)
            row['foreground_after']['hwnd'] = row['guard_after']['foreground']['hwnd'] = 100
            self.assert_rejected(binding, row)

    def test_owned_visible_window_and_noactivate_style_are_required_on_both_sides(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, original = self.receipt(directory, True, True)
            for phase in ('before', 'after'):
                for key, value in (('hwnd', 100), ('pid', 10), ('pid', 9.), ('noactivate', False),
                                   ('noactivate', 1), ('minimized', True), ('minimized', 0),
                                   ('width', 1), ('width', 9), ('height', None), ('height', 9)):
                    row = deepcopy(original)
                    row['guard_' + phase]['windows'][0][key] = value
                    with self.subTest(phase=phase, key=key, value=value):
                        self.assert_rejected(binding, row)
                for key, value in (('windows', []), ('windows', None), ('windows', [None]),
                                   ('window_noactivate', False), ('window_noactivate', 1)):
                    row = deepcopy(original)
                    row['guard_' + phase][key] = value
                    self.assert_rejected(binding, row)
            for key, value in (('hwnd', 100), ('pid', 10), ('pid', 9.), ('minimized', True),
                               ('width', 9), ('height', 9)):
                row = deepcopy(original)
                row['window'][key] = value
                self.assert_rejected(binding, row)

    def test_permission_cannot_waive_other_capture_gates(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, original = self.receipt(directory, True, True)
            for key, value in (('owner', 'other'), ('game_pid', 10), ('game_identity', '124'),
                               ('ok', False), ('reliable', False), ('native_resolution', False),
                               ('backend', 'PrintWindow'), ('variance', [0., 0., 0.]), ('sha256', '0' * 64)):
                row = dict(original, **{key: value})
                with self.subTest(key=key):
                    self.assert_rejected(binding, row)
            row = deepcopy(original)
            row['frame']['frame_qpc_100ns'] = 99
            self.assert_rejected(binding, row)

    def test_legacy_receipts_keep_strict_background_rules(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, row = self.receipt(directory, False, False)
            for key in ('foreground_policy', 'user_foreground_allowed', 'agent_activation_allowed',
                        'activation_fallback', 'noactivation_requested', 'guarded_no_activation',
                        'guard_before', 'guard_after'):
                del row[key]
            row.update(schema=2, background_only=True, background_safe=True)
            self.assertEqual([], capture_failures({'frame': row}, binding))
            self.assert_rejected(binding, dict(row, background_safe=False))
            self.assert_rejected(binding, dict(row, background_only=False))
            self.assert_rejected(binding, dict(row, user_foreground_allowed=True))
            self.assert_rejected(binding, dict(row, schema=4))


if __name__ == '__main__':
    unittest.main()
