"""Native GUI anchoring regressions; SDK/model IO is explicitly simulated."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path('behavior_pack/modern_projection/projection')
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import liquid_deployment, liquid_product_deployment as deployment
from projection import liquid_product_qualification_data as qualification
from projection.liquid_viewport import LiquidView
from tests import test_liquid_viewport as viewport_fixtures


def actual_definition(filename, kind, name, namespace):
    """Execute the original definition without importing the client-only UI."""
    path = ROOT / SOURCE / filename
    tree = ast.parse(path.read_text(encoding='utf8'), filename=str(path))
    nodes = [node for node in ast.walk(tree) if isinstance(node, kind) and node.name == name]
    if len(nodes) != 1:
        raise AssertionError('Expected one actual definition: ' + name)
    module = ast.fix_missing_locations(ast.Module(body=nodes, type_ignores=[]))
    exec(compile(module, str(path), 'exec'), namespace)
    return namespace[name]


class NativeGui:
    def __init__(self):
        self.logical, self.canvas = (499, 277), (1995, 1107, 0, 0)
        self.reads = [0, 0]

    def GetScreenViewInfo(self):
        self.reads[0] += 1
        return self.canvas

    def GetScreenSize(self):
        self.reads[1] += 1
        return self.logical


def theme_for(game):
    factory = SimpleNamespace(CreateGame=lambda unused: game)
    api = SimpleNamespace(GetEngineCompFactory=lambda: factory, GetLevelId=lambda: 'level')
    return actual_definition('widgets.py', ast.ClassDef, 'Theme',
                             {'Color': lambda value: value, 'clientApi': api})


class ProductWaterGuiTests(unittest.TestCase):
    def test_same_font_resize_refreshes_gui_without_extra_listener_notifications(self):
        game, notifications = NativeGui(), []
        theme = theme_for(game)
        theme.listeners.add(lambda value: notifications.append(value))
        for logical, canvas, gui in (
                ((499, 277), (1995, 1107, 0, 0), 4.),
                ((533, 300), (1600, 900, 0, 0), 3.),
                ((641, 360), (1281, 720, 0, 0), 2.)):
            with self.subTest(gui=gui):
                game.logical, game.canvas = logical, canvas
                theme.configure(3., True)
                self.assertEqual(gui, theme.native_gui_scale)
                self.assertEqual(5., theme.input_font_scale)
        self.assertEqual([(3., True, 5.)], notifications)
        self.assertEqual([3, 3], game.reads)

    def test_candidate_offsets_follow_integer_gui_and_reject_unknown_scale(self):
        for gui, expected in ((4, 75.), (3., 100.), (2, 150.)):
            with self.subTest(gui=gui):
                self.assertEqual((0., expected), deployment.ui_offset_for_gui((400., 300.), gui))
        for gui in (None, True, False, '2', 0, -1, 2.5, float('nan'), float('inf')):
            with self.subTest(gui=gui), self.assertRaises(ValueError):
                deployment.ui_offset_for_gui((400., 300.), gui)

    def test_dynamic_and_frozen_candidates_preserve_legacy_callback(self):
        for frozen in (False, True):
            profile = deployment.candidate_profile(frozen=frozen)
            self.assertIs(deployment.ui_offset_for_gui, profile.ui_offset_for_gui)
            self.assertIs(deployment.ui_geometry_for_gui, profile.ui_geometry_for_gui)
            self.assertIs(liquid_deployment.ui_offset, profile.ui_offset)
            self.assertEqual((0., 75.), profile.ui_offset((400., 300.)))

    def test_water_scene_reads_cached_gui_and_keeps_legacy_profiles(self):
        game = NativeGui()
        theme = theme_for(game)
        theme.configure(3., True)
        view = LiquidView((12., 24.), (400., 300.), 0., False)
        namespace = {'Theme': theme, 'liquid_profile': deployment.candidate_profile(),
                     'camera': None, 'session': SimpleNamespace(scene_origin=None, scene_size=None),
                     'native_width': 400., 'native_height': 300., 'cell_unit': 24.,
                     'group_view': lambda *unused: view}
        liquid_view = actual_definition('scene.py', ast.FunctionDef, 'liquid_view', namespace)
        before = list(game.reads)
        for gui, expected_height in ((4., 500.), (3., 566.6666666666667), (2., 700.)):
            theme.native_gui_scale = gui
            for unused in range(100):
                result = liquid_view((0, 0, 0))
                self.assertEqual(view.distance, result.distance)
                self.assertEqual(view.clipped, result.clipped)
                self.assertAlmostEqual(12., result.position[0])
                self.assertAlmostEqual(24., result.position[1])
                self.assertEqual(400., result.size[0])
                self.assertAlmostEqual(expected_height, result.size[1])
        self.assertEqual(before, game.reads)
        theme.native_gui_scale = None
        with self.assertRaises(ValueError):
            liquid_view((0, 0, 0))
        namespace['liquid_profile'] = SimpleNamespace(
            ui_offset_for_gui=deployment.ui_offset_for_gui, ui_offset=liquid_deployment.ui_offset)
        theme.native_gui_scale = 2.
        self.assertEqual(view._replace(position=(12., 174.)), liquid_view((0, 0, 0)))
        namespace['liquid_profile'] = SimpleNamespace(ui_offset=liquid_deployment.ui_offset)
        namespace['Theme'] = object()
        self.assertEqual(view._replace(position=(12., 99.)), liquid_view((0, 0, 0)))

    def test_same_ready_request_still_moves_native_geometry_without_resubmitting(self):
        fixture = viewport_fixtures.LiquidControlsTests()
        fixture.setUp()
        fixture.settle()
        ready = fixture.entry['ready_request']
        submissions = sum(len(control.doll.calls) for control in fixture.dolls)
        fixture.view = fixture.view._replace(position=(20., 150.), size=(640., 480.))
        self.assertTrue(fixture.update(.3))
        self.assertEqual(ready, fixture.entry['ready_request'])
        self.assertEqual((fixture.view.position, fixture.view.size), fixture.entry['geometry'])
        for control in fixture.dolls:
            self.assertEqual(fixture.view.position, control.position)
            self.assertEqual(fixture.view.size, control.size)
        calls = [control.position_calls for control in fixture.dolls]
        self.assertTrue(fixture.update(.4))
        self.assertEqual(calls, [control.position_calls for control in fixture.dolls])
        self.assertEqual(submissions, sum(len(control.doll.calls) for control in fixture.dolls))

    def test_explicit_candidate_cannot_grant_a_mismatched_production_contract(self):
        original = qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256
        with patch.object(qualification, 'QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256', '0' * 64):
            deployment.candidate_profile()
            deployment.candidate_profile(frozen=True)
            with self.assertRaisesRegex(ValueError, 'complete visible acceptance'):
                deployment.production_profile(deployment.TARGET_ENGINE_VERSION)
            self.assertEqual('0' * 64, qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256)
        self.assertEqual(original, qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256)


if __name__ == '__main__':
    unittest.main()
