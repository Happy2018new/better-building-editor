"""The native references use a stable camera shared by all six directions."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from verify_shulker_orientations import matching_camera, reference_offset, wait_camera_pose


class ShulkerCameraTests(unittest.TestCase):
    def test_reference_offset_keeps_every_direction_on_the_observed_low_side(self):
        self.assertEqual((-3.5, -3., -5.), reference_offset((-3.5, 3., -5.)))
        self.assertEqual((-3.5, -3., -5.), reference_offset((-3.5, -3., -5.)))

    def test_camera_uses_actual_interpolated_position_and_wrapped_sdk_yaw(self):
        pose = {'position': (3., -54.5, 1.5), 'rotation': (-26., -35.)}
        actual = {'position': (3., -54.5, 1.5), 'rotation': (-26., 145., 0.)}
        self.assertTrue(matching_camera(actual, pose))
        actual['rotation'] = (-26., -215., 0.)
        self.assertTrue(matching_camera(actual, pose))
        actual['position'] = (3., -48.5, 1.5)
        self.assertFalse(matching_camera(actual, pose))

    def test_pose_requires_two_consecutive_matching_samples_after_interpolation(self):
        pose = {'position': (3., -54.5, 1.5), 'rotation': (-26., -35.)}
        correct = {'position': (3., -54.5, 1.5), 'rotation': (-26., 145., 0.)}
        stale = dict(correct, position=(0., 64., 0.))

        class Check:
            def wait(self, label, predicate, read):
                outcomes = [predicate(value) for value in (correct, stale, correct, correct)]
                self.assertions = outcomes
                return correct

        check = Check()
        self.assertEqual(correct, wait_camera_pose(check, pose))
        self.assertEqual([False, False, False, True], check.assertions)


if __name__ == '__main__':
    unittest.main()
