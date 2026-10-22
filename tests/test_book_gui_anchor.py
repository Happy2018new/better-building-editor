"""Book anchors follow native GUI changes without changing resource or pose."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.book_profile import candidate_profile
from projection.liquid_viewport import LiquidView


def scene_book_view(namespace):
    """Exercise the real Scene closure while keeping all native UI IO absent."""
    path = ROOT / 'behavior_pack/modern_projection/projection/scene.py'
    tree = ast.parse(path.read_text('utf8'))
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name == 'book_view']
    if len(functions) != 1:
        raise AssertionError('Scene must have one book view callback')
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['book_view']


class BookGuiAnchorTests(unittest.TestCase):
    def test_recorded_gui2_and_gui3_displacement_and_gui4_identity(self):
        profile = candidate_profile()
        # R28 native A/B/A: logical Doll size and observed physical displacement.
        samples = ((2, (359.45573761668186, 184.112409010137), 92.05620450506848),
                   (3, (298.3797813472347, 153.4270075084475), 38.35675187711187),
                   (4, (282.36733144394674, 141.66427026613317), 0.))
        for gui, size, pixels in samples:
            with self.subTest(gui=gui):
                old = profile.ui_offset(size)
                new = profile.ui_offset_for_gui(size, gui)
                self.assertEqual(0., new[0])
                self.assertAlmostEqual(pixels, (new[1] - old[1]) * gui)
                if gui == 4:
                    self.assertEqual(old, new)

    def test_short_side_and_gui_boundaries_are_independent_of_orientation(self):
        profile = candidate_profile()
        for size in ((400., 120.), (120., 400.), (120., 120.)):
            for gui, logical in ((1, 120.), (2., 60.), (3, 40.), (4., 30.), (5, 24.)):
                with self.subTest(size=size, gui=gui):
                    self.assertEqual((0., logical), profile.ui_offset_for_gui(size, gui))

    def test_uninitialized_or_fractional_gui_is_rejected(self):
        profile = candidate_profile()
        for gui in (None, True, False, '2', 0, -1, .5, 2.5,
                    float('nan'), float('inf'), -float('inf')):
            with self.subTest(gui=gui), self.assertRaises(ValueError):
                profile.ui_offset_for_gui((400., 300.), gui)

    def test_scene_reads_live_native_cache_and_preserves_all_other_view_fields(self):
        profile = candidate_profile()
        original = LiquidView((12., 24.), (400., 300.), -2., False)
        theme = SimpleNamespace(native_gui_scale=2., scale=19.)
        calls = []

        def group_view(*args):
            calls.append(args)
            return original

        session = SimpleNamespace(scene_origin=(1, 2, 3), scene_size=(8, 4, 8))
        camera = object()
        namespace = {'book_profile': profile, 'Theme': theme, 'group_view': group_view,
                     'camera': camera, 'session': session, 'native_width': 400.,
                     'native_height': 300., 'cell_unit': 24.}
        actual = scene_book_view(namespace)
        # The same closure and group move across GUI changes and then return.
        for gui, y in ((2, 174.), (3, 124.), (4, 99.), (2, 174.)):
            theme.native_gui_scale = gui
            self.assertEqual(original._replace(position=(12., y)), actual((4, 0, 4)))
            self.assertEqual(((4, 0, 4), camera, (1, 2, 3), (8, 4, 8),
                              (400., 300.), 24.), calls[-1])

    def test_scene_supports_legacy_profiles_without_reading_gui_cache(self):
        original = LiquidView((12., 24.), (400., 300.), -2., False)
        profile = SimpleNamespace(ui_offset=lambda size: (3., 7.))
        namespace = {'book_profile': profile, 'Theme': object(), 'camera': None,
                     'session': SimpleNamespace(scene_origin=None, scene_size=None),
                     'native_width': 400., 'native_height': 300., 'cell_unit': 24.,
                     'group_view': lambda *args: original}
        self.assertEqual(original._replace(position=(15., 31.)),
                         scene_book_view(namespace)((0, 0, 0)))


if __name__ == '__main__':
    unittest.main()
