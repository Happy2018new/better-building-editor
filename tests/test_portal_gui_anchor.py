"""Portal anchors follow the live native GUI while retaining legacy profiles."""
import ast
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.portal_profile import candidate_profile
from projection.liquid_viewport import LiquidView


def scene_portal_view(namespace):
    """Call the real Scene closure with explicit native-IO boundaries."""
    path = ROOT / 'behavior_pack/modern_projection/projection/scene.py'
    tree = ast.parse(path.read_text('utf8'))
    functions = [node for node in ast.walk(tree)
                 if isinstance(node, ast.FunctionDef) and node.name == 'portal_view']
    if len(functions) != 1:
        raise AssertionError('Scene must have one portal view callback')
    module = ast.fix_missing_locations(ast.Module(body=functions, type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace['portal_view']


class PortalGuiAnchorTests(unittest.TestCase):
    def test_gui2_and_gui3_correction_and_gui4_identity(self):
        profile = candidate_profile()
        for size in ((400., 120.), (120., 400.)):
            old = profile.ui_offset(size)
            self.assertEqual((0., 30.), old)
            for gui, expected in ((2, (0., 60.)), (3., (0., 40.)), (4, old)):
                with self.subTest(size=size, gui=gui):
                    self.assertEqual(expected, profile.ui_offset_for_gui(size, gui))

    def test_gui_is_a_positive_integer_native_scale(self):
        profile = candidate_profile()
        for gui in (1, 1., 5, 5.):
            with self.subTest(gui=gui):
                self.assertEqual((0., 120. / gui), profile.ui_offset_for_gui((400., 120.), gui))
        for gui in (None, True, False, '2', 0, -1, .5, 2.5,
                    float('nan'), float('inf'), -float('inf')):
            with self.subTest(gui=gui), self.assertRaises(ValueError):
                profile.ui_offset_for_gui((400., 120.), gui)

    def test_same_callback_reads_each_live_gui_and_preserves_the_view(self):
        original = LiquidView((12., 24.), (400., 300.), -2., False)
        theme = SimpleNamespace(native_gui_scale=2., scale=19.)
        calls = []

        def group_view(*args):
            calls.append(args)
            return original

        camera = object()
        namespace = {'portal_profile': candidate_profile(), 'Theme': theme,
                     'group_view': group_view, 'camera': camera,
                     'session': SimpleNamespace(scene_origin=(1, 2, 3), scene_size=(8, 4, 8)),
                     'native_width': 400., 'native_height': 300., 'cell_unit': 24.}
        actual = scene_portal_view(namespace)
        for gui, y in ((2, 174.), (3, 124.), (4, 99.), (2, 174.)):
            theme.native_gui_scale = gui
            self.assertEqual(original._replace(position=(12., y)), actual((4, 0, 4)))
            self.assertEqual(((4, 0, 4), camera, (1, 2, 3), (8, 4, 8),
                              (400., 300.), 24.), calls[-1])
        self.assertEqual(4, len(calls))

    def test_legacy_and_explicit_none_hooks_do_not_read_gui(self):
        original = LiquidView((12., 24.), (400., 300.), -2., False)
        for explicit_none in (False, True):
            calls = []

            def legacy_offset(size):
                calls.append(size)
                return (3., 7.)

            profile = SimpleNamespace(ui_offset=legacy_offset)
            if explicit_none:
                profile.ui_offset_for_gui = None
            namespace = {'portal_profile': profile, 'Theme': object(), 'camera': None,
                         'session': SimpleNamespace(scene_origin=None, scene_size=None),
                         'native_width': 400., 'native_height': 300., 'cell_unit': 24.,
                         'group_view': lambda *args: original}
            with self.subTest(explicit_none=explicit_none):
                self.assertEqual(original._replace(position=(15., 31.)),
                                 scene_portal_view(namespace)((0, 0, 0)))
                self.assertEqual([original.size], calls)


if __name__ == '__main__':
    unittest.main()
