"""Independent multi-camera pose recovery and controlled budget aborts."""
import math
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import numpy as np
from scipy.optimize import least_squares

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_frame_block_multiview_r21 as analyzer
import item_sprite_calibration as calibration


def synthetic_view(angle, parameters=analyzer.CANDIDATE):
    position = [8, -39, 8]
    center = np.array([8.5, -38.5, 8.9375])
    radians = math.radians(angle)
    eye = center + [math.sin(radians) * 3., .5, -math.cos(radians) * 3.]
    direction = center - eye
    pitch = math.degrees(math.asin(-direction[1] / np.linalg.norm(direction)))
    yaw = math.degrees(math.atan2(direction[0], -direction[2]))
    view = {'position': position, 'camera': {'position': eye.tolist(), 'rotation': [pitch, yaw, 0.]},
            'size': (1280, 720), 'fov': 66.6, 'angle': float(angle)}
    contour = analyzer.polygon(analyzer.project_visible(view, parameters))
    view.update(contour=contour, observed_support=analyzer.support(contour, analyzer.DIRECTIONS))
    return view


class FrameBlockMultiview(unittest.TestCase):
    def test_oblique_holdouts_recover_an_independent_cube_pose(self):
        expected = [.28, .025, -.015, .4]
        fit = analyzer.joint_fit([synthetic_view(angle, expected) for angle in (-75, 0, 75)])
        np.testing.assert_allclose(fit['parameters_scale_cx_cy_cz'], expected, atol=1e-7)
        self.assertTrue(fit['depth_identifiable'])
        self.assertTrue(fit['support_clipping_certified'])
        self.assertLess(fit['support_max_pixels'], 1e-7)

    def test_a_single_view_does_not_qualify_absolute_depth(self):
        view = synthetic_view(0)
        fit = analyzer.joint_fit([view])
        self.assertFalse(fit['depth_identifiable'])
        self.assertFalse(fit['holdout_views_present'])
        def full_cube(values):
            return analyzer.support(analyzer.project(view['position'], values, view['camera'],
                view['size'], view['fov']), analyzer.DIRECTIONS)
        uncut = least_squares(lambda values: full_cube(values) - full_cube(analyzer.CANDIDATE), analyzer.CANDIDATE)
        singular = np.linalg.svd(uncut.jac, compute_uv=False)
        self.assertLess(singular[-1], singular[0] * 1e-6)

    def test_fixed_geometry_rejects_blank_shift_and_large_pose_error(self):
        view = synthetic_view(75)
        self.assertTrue(analyzer.geometry_row(view, analyzer.CANDIDATE)['passed'])
        shifted = dict(view, observed_support=analyzer.support(view['contour'] + [8., 0.], analyzer.DIRECTIONS))
        self.assertFalse(analyzer.geometry_row(shifted, analyzer.CANDIDATE)['passed'])
        self.assertFalse(analyzer.geometry_row(dict(view, contour=np.empty((0, 2))), analyzer.CANDIDATE)['passed'])
        self.assertFalse(analyzer.geometry_row(view, [.5, 0., 0., .1875])['passed'])
        self.assertFalse(analyzer.clipping_certified(view['position'], analyzer.CANDIDATE,
            dict(view['camera'], position=[8.5, -38.5, 9.1])))

    def test_calibration_budget_abort_precedes_capture_and_restores_saved_state(self):
        check = Mock()
        camera = {'position': [0., 0., 6.], 'rotation': [0., 0., 0.], 'screen': [1280, 720], 'fov': 60.}
        check.run.return_value = camera
        check.wait.side_effect = [{'mesh': [1, 2, 3]}, camera]
        check.navigation.return_value = {'open': False}
        saves = []
        with patch.object(calibration.time, 'sleep'), patch.object(calibration, 'capture') as capture:
            result = calibration.calibrate(check, {}, 'item-r20', Path('.'), Path('wgc.exe'),
                lambda name, value: saves.append((name, value)),
                before_capture=Mock(side_effect=RuntimeError('commit reserve reached')))
        capture.assert_not_called()
        self.assertFalse(result['passed'])
        self.assertTrue(result['restored'])
        self.assertIn('commit reserve reached', result['error'])
        self.assertTrue(any('del sys._item_camera_saved' in call.args[0] for call in check.run.call_args_list))
        self.assertEqual('camera.json', saves[-1][0])

    def test_every_calibration_capture_observes_the_budget_callback(self):
        check = Mock()
        camera = {'position': [0., 0., 6.], 'rotation': [0., 0., 0.],
                  'screen': [1280, 720], 'fov': 60., 'mesh': [1, 2, 3]}
        check.run.return_value = check.wait.return_value = camera
        check.navigation.return_value = {'open': False}
        events = []
        def captured(*args):
            events.append('capture')
            return {'width': 1280, 'height': 720}
        with patch.object(calibration.time, 'sleep'), patch.object(calibration, 'capture', side_effect=captured), \
                patch.object(calibration, 'camera_matches', return_value=True), \
                patch.object(calibration, 'analyze_calibration', side_effect=lambda row: row.update(passed=True)):
            result = calibration.calibrate(check, {'session_file': 'unused-session.json'}, 'item-r20', Path('.'), Path('wgc.exe'),
                lambda name, value: None, before_capture=lambda: events.append('budget'))
        self.assertTrue(result['passed'], result)
        self.assertEqual(['budget', 'capture'] * 6, events)


if __name__ == '__main__':
    unittest.main()
