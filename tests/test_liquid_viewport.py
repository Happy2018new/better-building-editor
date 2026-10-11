"""Water batch placement follows logical coordinates through orbit and clipping."""
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.camera import OrbitCamera
from projection.liquid_viewport import LiquidControls, LiquidView, group_view
from tests.test_liquid_render import Doll, Model, POSE, group


class LiquidViewportTests(unittest.TestCase):
    def test_native_rectangle_centers_on_the_same_projected_logical_point(self):
        camera = OrbitCamera(35., 25., 1.)
        camera.pan = (.15, -.1)
        scene_origin, scene_size = (10, 20, 30), (16, 12, 16)
        for yaw, pitch in ((0., 0.), (35., 25.), (90., 90.), (-135., -45.)):
            camera.yaw, camera.pitch = yaw, pitch
            view = group_view((12, 20, 32), camera, scene_origin, scene_size, (800., 600.), 20.)
            expected = camera.project((4., 2., 4.), scene_size, 800., 600., 20.)
            for axis in range(2):
                self.assertAlmostEqual(expected[axis], view.position[axis] + view.size[axis] / 2.)
            self.assertFalse(view.clipped)

    def test_depth_plane_changes_distance_without_moving_screen_position(self):
        camera = OrbitCamera(0., 0., 1.)
        front = group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.)
        camera.depth = 8.
        cut = group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.)
        self.assertEqual(front.position, cut.position)
        self.assertEqual(front.size, cut.size)
        self.assertAlmostEqual(front.distance + 8., cut.distance)
        self.assertFalse(cut.clipped)
        camera.depth = 13.
        self.assertTrue(group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.).clipped)

    def test_intersecting_batch_is_not_dropped_as_a_whole(self):
        camera = OrbitCamera(0., 0., 1.)
        camera.depth = 10.
        view = group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.)
        self.assertAlmostEqual(-.5, view.distance)
        self.assertFalse(view.clipped)

    def test_offscreen_culling_uses_full_batch_extent_after_pan(self):
        camera = OrbitCamera(0., 0., 1.)
        camera.pan = (1.1, 0.)
        self.assertTrue(group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.).clipped)
        camera.pan = (.5, 0.)
        self.assertFalse(group_view((4, 4, 4), camera, (0, 0, 0), (16,) * 3, (800., 600.), 20.).clipped)


class Control:
    def __init__(self, identity):
        self.position = self.size = None
        self.visible = True
        self.doll = Doll()
        self.doll.model_id = identity
        self.position_calls = 0

    def asNeteasePaperDoll(self):
        return self.doll

    def SetVisible(self, visible, unused):
        self.visible = visible

    def SetPosition(self, position):
        self.position = position
        self.position_calls += 1

    def SetSize(self, size):
        self.size = size


class RecordedModel(Model):
    def __init__(self):
        super().__init__()
        self.values = {}

    def SetExtraUniformValue(self, model_id, index, value):
        self.values[model_id, index] = value
        return super().SetExtraUniformValue(model_id, index, value)


class LiquidControlsTests(unittest.TestCase):
    def setUp(self):
        self.dolls = [Control(100), Control(101)]
        self.surfaces = [Control(200), Control(201)]
        self.entry = {'dolls': [SimpleNamespace(current=control) for control in self.dolls],
                      'surfaces': [SimpleNamespace(current=control) for control in self.surfaces]}
        self.registry = {0: self.entry}
        self.model = RecordedModel()
        self.controls = LiquidControls(self.registry, self.model)
        self.view = LiquidView((20., -10.), (800., 620.), -4., False)
        self.groups = {0: group()}

    def update(self, now):
        return self.controls.update(self.groups, lambda origin: self.view,
                                    lambda view: POSE, (-.5, -.25), now)

    def settle(self):
        for now in (0., .025, .05, .1, .2):
            ready = self.update(now)
        self.assertTrue(ready)

    def test_independent_controls_apply_geometry_and_clipping_before_visible_payload(self):
        self.assertFalse(self.update(0.))
        self.assertTrue(all(control.position == (-.5, -.25) for control in self.surfaces))
        self.assertTrue(all(control.position == self.view.position for control in self.dolls))
        self.assertTrue(all(control.size == self.view.size for control in self.dolls))
        self.assertEqual(0., self.model.values[(101, 4)][3])
        self.settle()
        self.assertFalse(self.surfaces[0].visible)
        self.assertTrue(self.surfaces[1].visible)
        self.assertEqual(.5, self.model.values[(101, 4)][3])

    def test_depth_motion_updates_uniform_without_model_or_layout_rebuild(self):
        self.settle()
        model_calls = sum(len(control.doll.calls) for control in self.dolls)
        positions = sum(control.position_calls for control in self.dolls)
        tag = self.model.values[(101, 4)][0]
        self.view = self.view._replace(distance=-3.)
        self.assertTrue(self.update(.3))
        self.assertNotEqual(tag, self.model.values[(101, 4)][0])
        self.assertEqual(model_calls, sum(len(control.doll.calls) for control in self.dolls))
        self.assertEqual(positions, sum(control.position_calls for control in self.dolls))

    def test_batch_pose_uses_current_native_size_after_pan_and_resize(self):
        observed = []
        def pose_at(view):
            observed.append(view.size)
            return (20. / min(view.size),) + POSE[1:]
        def update(now):
            return self.controls.update(self.groups, lambda origin: self.view,
                                        pose_at, (-.5, -.25), now)
        for now in (0., .025, .05, .1, .2):
            ready = update(now)
        self.assertTrue(ready)
        renderer = self.entry['renderer']
        first_pose = renderer.poses[renderer.front]
        first_payload = dict(self.model.values)
        self.view = self.view._replace(position=(-300., -200.), size=(1400., 1000.))
        self.assertTrue(update(.3))
        self.assertEqual(self.view.size, observed[-1])
        self.assertAlmostEqual(.02, renderer.poses[renderer.front][0])
        self.assertNotEqual(first_pose, renderer.poses[renderer.front])
        self.assertEqual(first_payload, self.model.values)

    def test_clipped_batch_does_not_request_a_native_pose(self):
        self.view = self.view._replace(clipped=True)
        def unexpected_pose(view):
            self.fail('A hidden batch does not need native coordinate calibration')
        self.assertTrue(self.controls.update(self.groups, lambda origin: self.view,
                                            unexpected_pose, (0., 0.), 0.))

    def test_stable_frame_does_not_repeat_native_id_queries(self):
        self.settle()
        def unexpected_query():
            self.fail('Unchanged water controls should not call GetModelId again')
        for control in self.dolls:
            control.doll.GetModelId = unexpected_query
        self.assertTrue(self.update(.3))
        self.assertTrue(self.update(.4))

    def test_retry_releases_failure_latch_and_reapplies_the_existing_request(self):
        self.dolls[1].doll.submit_ok = False
        self.assertFalse(self.update(0.))
        self.assertIsNotNone(self.controls.error)
        self.dolls[1].doll.submit_ok = True
        self.assertFalse(self.update(.1))
        self.controls.retry()
        for now in (.2, .225, .25, .3, .4):
            ready = self.update(now)
        self.assertTrue(ready)
        self.assertIsNone(self.controls.error)

    def test_invalid_pose_keeps_the_published_bank_and_native_layout_until_retry(self):
        self.settle()
        renderer = self.entry['renderer']
        for pose in ((0.,) + POSE[1:], (float('nan'),) + POSE[1:]):
            with self.subTest(pose=pose):
                old_layout = [(control.position, control.size) for control in self.dolls + self.surfaces]
                old_payload = dict(self.model.values)
                old_front = renderer.front
                old_request = self.entry['ready_request']
                old_calls = sum(len(control.doll.calls) for control in self.dolls)
                self.view = self.view._replace(position=(self.view.position[0] + 10., -20.),
                                               size=(1000., 800.))
                self.assertFalse(self.controls.update(self.groups, lambda origin: self.view,
                                                     lambda view: pose, (5., 10.), .3))
                self.assertTrue(self.controls.pending)
                self.assertIn('Liquid skeleton scale' if pose[0] == 0. else 'skeleton pose',
                              self.controls.error)
                self.assertEqual(old_layout,
                                 [(control.position, control.size) for control in self.dolls + self.surfaces])
                self.assertEqual(old_payload, self.model.values)
                self.assertEqual(old_front, renderer.front)
                self.assertEqual(old_request, self.entry['ready_request'])
                self.assertTrue(self.surfaces[old_front].visible)
                self.assertEqual(old_calls, sum(len(control.doll.calls) for control in self.dolls))
                self.assertFalse(self.update(.4))
                self.controls.retry()
                self.assertTrue(self.update(.5))
                self.assertIsNone(self.controls.error)
                self.assertTrue(all(control.position == self.view.position for control in self.dolls))

    def test_view_callback_failure_latches_once_and_removed_groups_still_hide(self):
        self.settle()
        calls = []
        def failed_view(origin):
            calls.append(origin)
            raise ValueError('Calibrated liquid offset is unavailable')
        for now in (.3, .4, .5):
            self.assertFalse(self.controls.update(self.groups, failed_view, lambda view: POSE,
                                                 (0., 0.), now))
            self.assertIn('Calibrated liquid offset', self.controls.error)
        self.assertEqual(1, len(calls))
        self.assertTrue(self.surfaces[self.entry['renderer'].front].visible)
        self.groups = {}
        self.assertTrue(self.controls.update(self.groups, failed_view, lambda view: POSE,
                                            (0., 0.), .6))
        self.assertIsNone(self.controls.error)
        self.assertFalse(any(control.visible for control in self.surfaces))
        self.assertEqual(1, len(calls))

    def test_invalid_depth_packet_does_not_apply_new_layout_or_request_pose(self):
        self.settle()
        old_layout = [(control.position, control.size) for control in self.dolls + self.surfaces]
        self.view = self.view._replace(position=(-200., -100.), size=(1400., 1000.), distance=512.)
        def unexpected_pose(view):
            self.fail('Invalid depth must be rejected before requesting a pose')
        self.assertFalse(self.controls.update(self.groups, lambda origin: self.view, unexpected_pose,
                                             (10., 20.), .3))
        self.assertIn('signed16 depth range', self.controls.error)
        self.assertEqual(old_layout,
                         [(control.position, control.size) for control in self.dolls + self.surfaces])
        self.view = self.view._replace(distance=-4.)
        self.controls.retry()
        self.assertTrue(self.update(.4))

    def test_pose_callback_failure_preserves_geometry_and_retry_can_resume(self):
        self.settle()
        old_geometry = self.entry['geometry']
        self.view = self.view._replace(position=(-200., -100.), size=(1400., 1000.))
        def failed_pose(view):
            raise ValueError('Liquid pose calibration could not resolve this viewport')
        self.assertFalse(self.controls.update(self.groups, lambda origin: self.view, failed_pose,
                                             (10., 20.), .3))
        self.assertIn('Liquid pose calibration', self.controls.error)
        self.assertEqual(old_geometry, self.entry['geometry'])
        self.assertTrue(all(control.position == old_geometry[0] for control in self.dolls))
        self.controls.retry()
        self.assertTrue(self.update(.4))
        self.assertEqual((self.view.position, self.view.size), self.entry['geometry'])

    def test_one_failed_adapter_does_not_stop_other_owned_entries(self):
        self.settle()
        dolls, surfaces = [Control(110), Control(111)], [Control(210), Control(211)]
        healthy = {'dolls': [SimpleNamespace(current=control) for control in dolls],
                   'surfaces': [SimpleNamespace(current=control) for control in surfaces]}
        self.registry[1] = healthy
        self.groups[1] = group(1)._replace(origin=(8, 0, 8))
        failed_origin = self.groups[0].origin
        def view_at(origin):
            if origin == failed_origin:
                raise ValueError('First liquid group cannot be calibrated')
            return self.view
        for now in (.3, .325, .35, .4, .5):
            self.assertFalse(self.controls.update(self.groups, view_at, lambda view: POSE,
                                                 (-.5, -.25), now))
        self.assertIn('First liquid group', self.controls.error)
        self.assertIn('ready_request', healthy)
        self.assertTrue(surfaces[healthy['renderer'].front].visible)
        self.assertTrue(self.surfaces[self.entry['renderer'].front].visible)

    def test_replacing_invalid_source_group_recovers_without_explicit_retry(self):
        self.settle()
        original = self.groups[0]
        self.groups[0] = original._replace(uniforms=original.uniforms[:3] +
            (original.uniforms[3][:3] + (2.,),))
        self.assertFalse(self.update(.3))
        self.assertIn('projection opacity', self.controls.error)
        self.assertTrue(self.surfaces[self.entry['renderer'].front].visible)
        self.assertFalse(self.update(.4))
        corrected = group(height=.3)
        self.groups[0] = corrected
        for now in (.5, .525, .55, .6, .7):
            ready = self.update(now)
        self.assertTrue(ready)
        self.assertIsNone(self.controls.error)
        self.assertEqual(corrected.uniforms[:3], self.entry['ready_request'][0].uniforms[:3])
        self.assertTrue(self.surfaces[self.entry['renderer'].front].visible)

    def test_viewport_restore_clears_adapter_latch_and_prepares_current_view(self):
        self.settle()
        self.assertFalse(self.controls.update(self.groups, lambda origin: self.view,
                                             lambda view: (0.,) + POSE[1:], (0., 0.), .3))
        self.view = self.view._replace(position=(-200., -100.), size=(1400., 1000.))
        self.controls.invalidate()
        self.assertFalse(any(control.visible for control in self.surfaces))
        for now in (.4, .425, .45, .5, .6):
            ready = self.update(now)
        self.assertTrue(ready)
        self.assertIsNone(self.controls.error)
        self.assertEqual((self.view.position, self.view.size), self.entry['geometry'])

    def test_offscreen_and_removed_groups_hide_all_banks_and_resume_owned_controls(self):
        self.settle()
        self.view = self.view._replace(clipped=True)
        self.assertTrue(self.update(.3))
        self.assertFalse(any(control.visible for control in self.surfaces))
        self.view = self.view._replace(clipped=False)
        for now in (.4, .425, .45, .5):
            self.update(now)
        self.assertTrue(any(control.visible for control in self.surfaces))
        self.groups = {}
        self.assertTrue(self.update(.6))
        self.assertFalse(any(control.visible for control in self.surfaces))

    def test_mount_wait_and_view_restore_do_not_claim_readiness(self):
        self.registry.clear()
        self.assertFalse(self.update(0.))
        self.registry[0] = self.entry
        self.entry['dolls'][0].current = None
        self.assertFalse(self.update(.1))
        self.entry['dolls'][0].current = self.dolls[0]
        self.settle()
        self.controls.invalidate()
        self.assertFalse(any(control.visible for control in self.surfaces))
        self.assertFalse(self.update(.4))
        self.controls.close()
        self.assertFalse(any(control.visible for control in self.surfaces))
        self.assertFalse(self.update(.5))
