"""Native geometry must not hide changes to the original public blueprint state."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_static_neighbor_world_visuals import native_state_comparison
from verify_neighbor_native_png import restore_owned_window


class StaticNeighborStateAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.value = ('minecraft:fence_gate', 0)
        self.source = {'origin': (20, 30, -10), 'cells': [((1, 2, 3), self.value)]}
        self.native = {'cells': [((21, 32, -7), self.value)]}

    def test_original_state_matches_native_at_world_position(self):
        self.assertTrue(native_state_comparison(self.source, self.native)['passed'])

    def test_same_material_with_changed_aux_cannot_pass(self):
        native = {'cells': [((21, 32, -7), ('minecraft:fence_gate', 4))]}
        result = native_state_comparison(self.source, native)
        self.assertFalse(result['passed'])
        self.assertEqual([{'position': (21, 32, -7), 'requested': self.value,
                           'actual': ('minecraft:fence_gate', 4)}], result['changes'])

    def test_incomplete_extra_duplicate_and_empty_snapshots_cannot_pass(self):
        snapshots = ({'cells': []},
                     {'cells': self.native['cells'] + [((22, 32, -7), self.value)]},
                     {'cells': self.native['cells'] * 2})
        for snapshot in snapshots:
            with self.subTest(snapshot=snapshot):
                self.assertFalse(native_state_comparison(self.source, snapshot)['passed'])
        self.assertFalse(native_state_comparison({'origin': (0, 0, 0), 'cells': []}, {'cells': []})['passed'])

    def test_background_route_never_resolves_or_activates_a_window(self):
        from unittest.mock import patch
        import release_owned_game_focus
        with patch.object(release_owned_game_focus, 'owned_game_hwnd',
                          side_effect=AssertionError('Background checks must not select a desktop window')):
            result = restore_owned_window({'game_pid': 123}, background_only=True)
        self.assertFalse(result['activation_attempted'])
        self.assertFalse(result['restored'])
        self.assertTrue(result['background_only'])


if __name__ == '__main__':
    unittest.main()
