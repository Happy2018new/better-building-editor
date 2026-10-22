"""Recorded water readiness geometry; no native rendering is simulated as proof."""
import ast
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'behavior_pack', 'modern_projection'))
from projection import liquid_deployment, liquid_product_deployment as deployment
from projection.liquid_viewport import LiquidView


def intersection(position, size, clip_position, clip_size):
    return (max(0., min(position[0] + size[0], clip_position[0] + clip_size[0]) - max(position[0], clip_position[0])) *
            max(0., min(position[1] + size[1], clip_position[1] + clip_size[1]) - max(position[1], clip_position[1])))


def native_anchor(position, size, gui):
    return position[0] + size[0] / 2., position[1] + size[1] / 2. - min(size) / gui


class ProductWaterGeometryTests(unittest.TestCase):
    def test_actual_scene_hook_precedence_legacy_fallback_and_pose_scaling(self):
        # Execute the actual two callbacks in both supported Python versions.
        path = os.path.join(ROOT, 'behavior_pack', 'modern_projection', 'projection', 'scene.py')
        with open(path, 'rb') as stream:
            tree = ast.parse(stream.read(), filename=path)
        nodes = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
                 and node.name in ('liquid_view', 'liquid_pose')]
        self.assertEqual(2, len(nodes))
        module = ast.Module(body=nodes)
        module.type_ignores = []
        theme = type('Theme', (), {'native_gui_scale': 4.})()
        session = type('Session', (), {'scene_origin': None, 'scene_size': None})()
        profile = deployment.candidate_profile()

        def unexpected_offset(unused):
            raise AssertionError('Geometry hook must take precedence over offsets')

        profile.ui_offset = unexpected_offset
        profile.ui_offset_for_gui = unexpected_offset
        view = LiquidView((12., 24.), (400., 100.), -2., True)
        namespace = {'Theme': theme, 'session': session, 'liquid_profile': profile,
                     'group_view': lambda *args: view, 'camera': None,
                     'native_width': 400., 'native_height': 300., 'cell_unit': 52.9092,
                     'rendered_pitch': 25., 'rendered_yaw': 35.}
        eval(compile(module, path, 'exec'), namespace)
        adjusted = namespace['liquid_view']((4, 0, 4))
        self.assertEqual(LiquidView((12., -26.), (400., 400.), -2., True), adjusted)
        pose = namespace['liquid_pose'](adjusted)
        self.assertAlmostEqual(52.9092, pose[0] * min(adjusted.size))
        legacy = type('Profile', (), {})()
        legacy.ui_offset = lambda size: (3., 7.)
        legacy.ui_offset_for_gui = deployment.ui_offset_for_gui
        namespace['liquid_profile'] = legacy
        self.assertEqual(view._replace(position=(12., 49.)), namespace['liquid_view']((4, 0, 4)))
        del legacy.ui_offset_for_gui
        namespace['Theme'] = object()
        self.assertEqual(view._replace(position=(15., 31.)), namespace['liquid_view']((4, 0, 4)))

    def test_recorded_failed_pool_rect_overlaps_actual_clip_after_geometry_hook(self):
        # R28 failed F: rect moved below the actual clip while its water stayed in view.
        position, size = (0., 0.), (366.6114179110209, 413.8419953612879)
        clip_position, clip_size = (0., .125), (340., 159.)
        old_position = (0., 183.30570895551046)
        self.assertEqual(0., intersection(old_position, size, clip_position, clip_size))
        adjusted_position, adjusted_size = deployment.ui_geometry_for_gui(position, size, 2.)
        self.assertAlmostEqual(0., adjusted_position[0])
        self.assertAlmostEqual(0., adjusted_position[1])
        self.assertAlmostEqual(366.6114179110209, adjusted_size[0])
        self.assertAlmostEqual(780.4534132723088, adjusted_size[1])
        self.assertEqual(54060., intersection(adjusted_position, adjusted_size, clip_position, clip_size))

    def test_gui_changes_preserve_anchor_and_effective_pixel_unit_for_both_aspects(self):
        # Pixel extent depends on scale*min(size), not raw scale. The width branch
        # is exercised by landscape GUI4; portrait cases need a different scale.
        for position, size in (((-30., -20.), (400., 100.)), ((12., 24.), (100., 400.)),
                               ((0., 0.), (366.6114179110209, 413.8419953612879))):
            for gui in (1., 2., 3., 4., 8., 16., 256.):
                adjusted_position, adjusted_size = deployment.ui_geometry_for_gui(position, size, gui)
                anchor = native_anchor(adjusted_position, adjusted_size, gui)
                self.assertAlmostEqual(position[0] + size[0] / 2., anchor[0])
                self.assertAlmostEqual(position[1] + size[1] / 2., anchor[1])
                self.assertLessEqual(adjusted_position[0], position[0] + 1e-7)
                self.assertLessEqual(adjusted_position[1], position[1] + 1e-7)
                for axis in (0, 1):
                    self.assertGreaterEqual(adjusted_position[axis] + adjusted_size[axis],
                                            position[axis] + size[axis] - 1e-7)
                for unit in (.125, 52.9092, 300.):
                    pose = liquid_deployment.ui_pose(unit, 25., 35., adjusted_size)
                    self.assertAlmostEqual(unit, pose[0] * min(adjusted_size))

    def test_native_pixels_change_if_resizing_does_not_recalculate_pose(self):
        old_size = (366.6114179110209, 413.8419953612879)
        new_size = deployment.ui_geometry_for_gui((0., 0.), old_size, 2.)[1]
        # This near-square sample keeps width as its minimum. Use a landscape
        # control to catch an implementation that retains the pre-resize pose.
        self.assertEqual(min(old_size), min(new_size))
        landscape = (400., 100.)
        expanded = deployment.ui_geometry_for_gui((-30., -20.), landscape, 4.)[1]
        old_scale = liquid_deployment.ui_pose(52.9092, 25., 35., landscape)[0]
        self.assertNotAlmostEqual(52.9092, old_scale * min(expanded))
        new_scale = liquid_deployment.ui_pose(52.9092, 25., 35., expanded)[0]
        self.assertAlmostEqual(52.9092, new_scale * min(expanded))

    def test_invalid_gui_or_geometry_never_produces_a_native_rectangle(self):
        for gui in (None, True, False, '2', 0, -1, .5, 2.5,
                    float('nan'), float('inf'), -float('inf')):
            with self.assertRaises(ValueError):
                deployment.ui_geometry_for_gui((0., 0.), (400., 300.), gui)
        for position, size in (((0.,), (400., 300.)), ((0., 0.), (400.,)),
                               ((0., 0.), (0., 300.)), ((0., 0.), (-1., 300.)),
                               ((True, 0.), (400., 300.)), ((0., 0.), (400., False)),
                               ((0., float('nan')), (400., 300.)),
                               ((float('inf'), 0.), (400., 300.)),
                               ((0., 0.), (400., -float('inf'))),
                               (('0', 0.), (400., 300.))):
            with self.assertRaises(ValueError):
                deployment.ui_geometry_for_gui(position, size, 2.)


if __name__ == '__main__':
    unittest.main()
