"""Owned renderer transactions, readiness and cleanup without a live SDK."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.liquid_render import SkeletonLiquidRenderer, WorldLiquidRenderer
from projection.liquid_transport import RenderGroup, pack_group
from tests.test_liquid_transport import surface

POSE = (.15, -55., 0., 0.)
ANCHOR = (10., 64., 20.)


def group(key=0, height=.7):
    return RenderGroup(key, 'native_liquid_model', (4, 0, 8),
                       pack_group((0, 0, 0), (surface(heights=(height,) * 4),),
                                  (18, 52, 86), None, .5))


class Doll:
    def __init__(self):
        self.calls = []
        self.model_id = -1
        self.submit_ok = True

    def RenderSkeletonModel(self, params):
        self.calls.append(params)
        return self.submit_ok

    def GetModelId(self):
        return self.model_id


class Model:
    def __init__(self):
        self.calls = []
        self.ok = True

    def SetExtraUniformValue(self, model_id, index, value):
        self.calls.append((model_id, index, value))
        return self.ok


class SkeletonLiquidTests(unittest.TestCase):
    def setUp(self):
        self.dolls, self.model, self.shown = (Doll(), Doll()), Model(), {}
        self.renderer = SkeletonLiquidRenderer(self.dolls, self.model, self.shown.__setitem__)

    def settle(self, value, start, model_id):
        self.renderer.update(value, POSE, start)
        back = 1 - self.renderer.front
        self.dolls[back].model_id = model_id
        self.renderer.update(value, POSE, start + .03)
        self.renderer.update(value, POSE, start + .06)
        return self.renderer.update(value, POSE, start + .09)

    def test_ids_are_asynchronous_and_payload_precedes_visible_promotion(self):
        value = group()
        self.assertFalse(self.renderer.update(value, POSE, 0.))
        self.assertFalse(self.renderer.update(value, POSE, .03))
        self.assertEqual([], self.model.calls)
        self.assertEqual({0: False, 1: True}, self.shown)
        self.dolls[1].model_id = 1
        self.assertFalse(self.renderer.update(value, POSE, .06))
        self.assertEqual(4, len(self.model.calls))
        self.assertEqual((1, 4, value.uniforms[3][:3] + (0.,)), self.model.calls[0])
        self.assertTrue(self.renderer.update(value, POSE, .09))
        self.assertEqual((1, 4, value.uniforms[3]), self.model.calls[-1])
        self.assertEqual({0: False, 1: True}, self.shown)
        self.assertTrue(self.renderer.update(value, POSE, .12))
        self.assertEqual(5, len(self.model.calls))

    def test_replacement_retains_old_surface_and_cancels_stale_pending_payload(self):
        first, second, third = group(height=.7), group(height=.3), group(height=.5)
        self.assertTrue(self.settle(first, 0., 1))
        self.renderer.update(second, POSE, 1.)
        self.renderer.update(third, POSE, 1.01)
        self.assertEqual({0: True, 1: True}, self.shown)
        self.assertEqual((third, POSE), self.renderer.pending)
        self.dolls[0].model_id = 2
        for now in (1.04, 1.07, 1.10):
            self.renderer.update(third, POSE, now)
        self.assertEqual({0: True, 1: False}, self.shown)
        self.assertEqual(10, len(self.model.calls))

    def test_timeout_is_latched_until_explicit_retry_without_recreating_each_frame(self):
        value = group()
        self.renderer.update(value, POSE, 0.)
        self.assertFalse(self.renderer.update(value, POSE, 2.1))
        self.assertIn('did not become ready', self.renderer.error)
        for frame in range(100):
            self.renderer.update(value, POSE, 3. + frame / 60.)
        self.assertEqual(1, len(self.dolls[1].calls))
        self.renderer.retry()
        self.renderer.update(value, POSE, 5.)
        self.assertEqual(2, len(self.dolls[1].calls))

    def test_pose_model_id_change_reapplies_payload_to_new_owned_id(self):
        value = group()
        self.assertTrue(self.settle(value, 0., 1))
        original = self.dolls[1].RenderSkeletonModel
        def replace(params):
            self.dolls[1].model_id = 5
            return original(params)
        self.dolls[1].RenderSkeletonModel = replace
        self.assertTrue(self.renderer.update(value, (.15, -45., 0., 0.), 1.))
        self.assertEqual([5] * 4, [call[0] for call in self.model.calls[-4:]])

    def test_continuous_same_group_pose_updates_keep_front_payload_and_id(self):
        value = group()
        self.assertTrue(self.settle(value, 0., 1))
        calls = len(self.model.calls)
        for frame in range(16):
            pose = (.15, -55., float(frame + 1) * 3., 0.)
            self.assertTrue(self.renderer.update(value, pose, 1. + frame / 60.))
            self.assertIsNone(self.renderer.pending)
            self.assertEqual(1, self.renderer.front)
            self.assertEqual({0: False, 1: True}, self.shown)
        self.assertEqual(calls, len(self.model.calls))

    def test_failed_active_pose_submission_keeps_previous_pose_and_payload(self):
        value = group()
        self.assertTrue(self.settle(value, 0., 1))
        self.dolls[1].submit_ok = False
        self.assertFalse(self.renderer.update(value, (.15, -45., 0., 0.), 1.))
        self.assertEqual(POSE, self.renderer.poses[1])
        self.assertEqual({0: False, 1: True}, self.shown)

    def test_continuous_orbit_during_shape_replace_keeps_front_moving_and_promotes_latest_pose(self):
        self.assertTrue(self.settle(group(), 0., 1))
        value = group(height=.3)
        old_calls = len(self.dolls[1].calls)
        initial_pose = (.15, -55., 3., 0.)
        self.renderer.update(value, initial_pose, 1.)
        self.dolls[0].model_id = 2
        for frame in range(1, 6):
            final_pose = (.15, -55., float(frame + 1) * 3., 0.)
            ready = self.renderer.update(value, final_pose, 1. + frame / 60.)
            if frame < 5:
                self.assertFalse(ready)
                self.assertEqual((value, initial_pose), self.renderer.pending)
                self.assertEqual(1, len(self.dolls[0].calls))
                self.assertEqual(final_pose, self.renderer.poses[1])
                self.assertEqual({0: True, 1: True}, self.shown)
        self.assertTrue(ready)
        self.assertIsNone(self.renderer.pending)
        self.assertEqual(old_calls + 6, len(self.dolls[1].calls))
        self.assertEqual(2, len(self.dolls[0].calls))
        self.assertEqual(final_pose, self.renderer.poses[self.renderer.front])
        self.assertEqual({0: True, 1: False}, self.shown)

    def test_initial_shape_becomes_ready_during_continuous_orbit(self):
        value = group()
        self.renderer.update(value, POSE, 0.)
        self.dolls[1].model_id = 1
        for frame in range(1, 6):
            pose = (.15, -55., float(frame) * 3., 0.)
            ready = self.renderer.update(value, pose, frame / 60.)
        self.assertTrue(ready)
        self.assertEqual(2, len(self.dolls[1].calls))
        self.assertEqual(pose, self.renderer.poses[1])
        self.assertIsNone(self.renderer.pending)

    def test_failed_shape_latches_during_orbit_and_keeps_previous_front_moving(self):
        self.assertTrue(self.settle(group(), 0., 1))
        value = group(height=.3)
        self.renderer.update(value, POSE, 1.)
        self.dolls[0].model_id = 2
        original = self.model.SetExtraUniformValue
        self.model.SetExtraUniformValue = lambda model_id, index, data: (
            False if model_id == 2 and index == 2 else original(model_id, index, data))
        self.renderer.update(value, POSE, 1.03)
        self.assertFalse(self.renderer.update(value, POSE, 1.06))
        failure = self.renderer.error
        for frame in range(16):
            pose = (.15, -55., float(frame + 1) * 3., 0.)
            self.assertFalse(self.renderer.update(value, pose, 1.1 + frame / 60.))
            self.assertEqual(1, self.renderer.front)
            self.assertEqual(pose, self.renderer.poses[1])
            self.assertEqual(failure, self.renderer.error)
            self.assertEqual({0: False, 1: True}, self.shown)
        self.assertEqual(1, len(self.dolls[0].calls))
        self.assertIsNone(self.renderer.pending)

    def test_latest_pose_failure_does_not_unmask_or_promote_incoming_shape(self):
        self.assertTrue(self.settle(group(), 0., 1))
        value = group(height=.3)
        self.renderer.update(value, POSE, 1.)
        self.dolls[0].model_id = 2
        self.renderer.update(value, POSE, 1.03)
        self.renderer.update(value, POSE, 1.06)
        self.dolls[0].submit_ok = False
        pose = (.15, -55., 30., 0.)
        self.assertFalse(self.renderer.update(value, pose, 1.09))
        self.assertEqual(1, self.renderer.front)
        self.assertEqual(pose, self.renderer.poses[1])
        self.assertEqual(0., self.renderer.uniforms[0][4][3])
        self.assertEqual({0: False, 1: True}, self.shown)

    def test_second_uniform_failure_does_not_promote_partial_payload(self):
        value = group()
        self.assertTrue(self.settle(value, 0., 1))
        self.renderer.update(group(height=.3), POSE, 1.)
        self.dolls[0].model_id = 2
        original = self.model.SetExtraUniformValue
        self.model.SetExtraUniformValue = lambda model_id, index, data: (
            False if index == 2 else original(model_id, index, data))
        self.renderer.update(group(height=.3), POSE, 1.03)
        self.assertFalse(self.renderer.update(group(height=.3), POSE, 1.06))
        self.assertEqual({0: False, 1: True}, self.shown)
        self.assertEqual(2, len(self.renderer.uniforms[0]))

    def test_reused_bank_is_masked_before_native_submission(self):
        self.assertTrue(self.settle(group(height=.7), 0., 1))
        self.assertTrue(self.settle(group(height=.3), 1., 2))
        value = group(height=.5)
        self.renderer.update(value, POSE, 2.)
        self.assertEqual((1, 4, value.uniforms[3][:3] + (0.,)), self.model.calls[-1])
        self.assertEqual({0: True, 1: True}, self.shown)

    def test_mask_failure_keeps_old_front_and_latches_without_new_submission(self):
        self.assertTrue(self.settle(group(height=.7), 0., 1))
        self.assertTrue(self.settle(group(height=.3), 1., 2))
        before = len(self.dolls[1].calls)
        self.model.ok = False
        value = group(height=.5)
        self.assertFalse(self.renderer.update(value, POSE, 2.))
        self.assertIn('mask preparing', self.renderer.error)
        self.assertEqual(before, len(self.dolls[1].calls))
        self.assertEqual({0: True, 1: False}, self.shown)

    def test_model_ids_must_be_independent_and_close_is_idempotent(self):
        self.assertTrue(self.settle(group(height=.7), 0., 1))
        value = group(height=.3)
        self.renderer.update(value, POSE, 1.)
        self.dolls[0].model_id = 1
        self.renderer.update(value, POSE, 1.03)
        self.assertFalse(self.renderer.update(value, POSE, 1.06))
        self.assertIn('independent IDs', self.renderer.error)
        self.assertEqual({0: False, 1: True}, self.shown)
        self.renderer.close()
        self.renderer.close()
        self.assertEqual({0: False, 1: False}, self.shown)
        self.assertFalse(self.renderer.update(group(), POSE, 2.))


class Runtime:
    def __init__(self):
        self.factory = self.system = self
        self.level = 'native-level-owner'
        self.alive = True
        self.models, self.positions = {}, {}
        self.removed, self.uniform_calls = [], []
        self.position_ok = self.uniforms_ok = self.remove_ok = True
        self.fail_show_model = self.fail_uniform_index = self.fail_move_model = None
        self.serial = self.peak_live = 0

    def CreateModel(self, level):
        assert level == self.level
        return self

    def CreateFreeModel(self, name, dimension):
        self.serial += 1
        self.models[self.serial] = {'name': name, 'dimension': dimension, 'uniforms': {}}
        self.peak_live = max(self.peak_live, len(self.models))
        return self.serial

    def SetFreeModelPos(self, model, x, y, z):
        if not self.position_ok or model == self.fail_move_model:
            return False
        self.positions[model] = x, y, z
        return True

    def SetFreeModelScale(self, model, x, y, z):
        self.models[model]['scale'] = x, y, z
        return True

    def SetFreeModelRot(self, model, x, y, z):
        self.models[model]['rotation'] = x, y, z
        return True

    def SetExtraUniformValue(self, model, index, value):
        if (not self.uniforms_ok or index == self.fail_uniform_index or
                index == 4 and value[3] > 0. and model == self.fail_show_model):
            return False
        self.models[model]['uniforms'][index] = value
        self.uniform_calls.append((model, index, value))
        return True

    def RemoveFreeModel(self, model):
        if not self.remove_ok:
            return False
        self.removed.append(model)
        del self.models[model]
        self.positions.pop(model, None)
        return True

    def hidden(self, model):
        return self.models[model]['uniforms'][4][3] == 0.


class WorldLiquidTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.renderer = WorldLiquidRenderer(self.runtime, 4, 0, (1.,) * 3, (0., 180., 0.))

    def settle(self, groups, now):
        self.assertTrue(self.renderer.begin(groups, ANCHOR, now))
        for delay in (.19, .21, .24, .27, .31):
            ready = self.renderer.advance(now + delay)
        self.assertTrue(ready)

    def test_masked_warmup_keeps_previous_generation_visible(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['model_id']
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.19))
        self.assertFalse(self.renderer.advance(1.21))
        self.assertFalse(self.runtime.hidden(old))
        staged = self.renderer.staging[0]['model_id']
        self.assertTrue(self.runtime.hidden(staged))
        self.assertEqual(4, len(self.runtime.models[staged]['uniforms']))
        self.assertEqual((1.,) * 3, self.runtime.models[staged]['scale'])
        self.assertEqual((0., 180., 0.), self.runtime.models[staged]['rotation'])
        self.assertEqual(0, self.runtime.models[staged]['dimension'])
        self.assertEqual((16., 66., 30.), self.runtime.positions[staged])
        for now in (1.24, 1.27, 1.31):
            self.renderer.advance(now)
        self.assertEqual([old], self.runtime.removed)
        self.assertFalse(self.runtime.hidden(staged))

    def test_many_replacements_never_exceed_two_bounded_generations_and_cleanup_all(self):
        for iteration in range(100):
            self.settle(tuple(group(key, iteration / 100.) for key in range(4)), float(iteration))
        self.assertEqual(8, self.runtime.peak_live)
        self.assertEqual(4, len(self.runtime.models))
        self.assertTrue(self.renderer.close())
        self.assertTrue(self.renderer.close())
        self.assertEqual({}, self.runtime.models)
        self.assertEqual(400, len(self.runtime.removed))

    def test_unchanged_groups_and_anchor_motion_reuse_owned_instances_and_payload(self):
        groups = (group(),)
        self.settle(groups, 0.)
        calls = len(self.runtime.uniform_calls)
        self.assertTrue(self.renderer.begin(groups, (11., 65., 21.), 1.))
        self.assertEqual(1, self.runtime.serial)
        self.assertEqual(calls, len(self.runtime.uniform_calls))
        model = self.renderer.active[0]['model_id']
        self.assertEqual((17., 67., 31.), self.runtime.positions[model])

    def test_failed_position_preserves_active_and_cleans_staging(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['model_id']
        self.runtime.position_ok = False
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual([old], list(self.runtime.models))
        self.assertEqual({}, self.renderer.staging)
        self.assertIn('position', self.renderer.error)
        self.assertFalse(self.runtime.hidden(old))

    def test_failed_mask_removes_created_model_and_preserves_active(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['model_id']
        self.runtime.uniforms_ok = False
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual([old], list(self.runtime.models))
        self.assertEqual(2, self.runtime.removed[-1])

    def test_budget_rejection_and_duplicate_keys_leave_existing_pending_transaction(self):
        self.renderer.begin((group(),), ANCHOR, 0.)
        self.renderer.advance(.01)
        staged = self.renderer.staging[0]['model_id']
        for groups in (tuple(group(key) for key in range(5)), (group(), group())):
            with self.assertRaises(ValueError):
                self.renderer.begin(groups, ANCHOR, .1)
        self.assertEqual(staged, self.renderer.staging[0]['model_id'])
        self.assertEqual([], self.runtime.removed)

    def test_cancel_empty_hide_and_bridge_shutdown_cleanup_owned_models(self):
        self.settle((group(),), 0.)
        self.assertTrue(self.renderer.set_visible(False))
        self.assertTrue(self.runtime.hidden(next(iter(self.runtime.models))))
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertTrue(self.renderer.begin((), ANCHOR, 1.1))
        self.assertEqual({}, self.runtime.models)
        self.renderer.begin((group(),), ANCHOR, 2.)
        self.runtime.alive = False
        self.assertFalse(self.renderer.advance(2.3))
        self.assertEqual({}, self.runtime.models)

    def test_remove_failure_retains_ownership_and_retries_after_close(self):
        self.settle((group(),), 0.)
        self.runtime.remove_ok = False
        self.assertFalse(self.renderer.close())
        self.assertEqual(1, len(self.runtime.models))
        self.assertEqual(1, len(self.renderer.retired))
        self.assertEqual(1, len(self.renderer.cleanup_errors))
        self.runtime.remove_ok = True
        self.assertTrue(self.renderer.advance(1.))
        self.assertEqual({}, self.runtime.models)

    def test_retired_models_count_toward_budget_after_failed_replacements(self):
        self.renderer = WorldLiquidRenderer(self.runtime, 1, 0, (1.,) * 3, (0., 180., 0.))
        self.settle((group(height=.7),), 0.)
        self.runtime.remove_ok = False
        self.settle((group(height=.3),), 1.)
        self.assertEqual(1, len(self.renderer.retired))
        self.assertFalse(self.renderer.begin((group(height=.5),), ANCHOR, 2.))
        self.assertEqual(2, self.runtime.peak_live)
        self.assertEqual(2, len(self.runtime.models))
        self.assertIn('Retired', self.renderer.error)
        self.runtime.remove_ok = True
        self.settle((group(height=.5),), 3.)
        self.assertEqual(1, len(self.runtime.models))

    def test_middle_visibility_failure_restores_old_models_and_cleans_new(self):
        self.settle((group(0), group(1)), 0.)
        old = tuple(record['model_id'] for record in self.renderer.active.values())
        self.renderer.set_visible(False)
        self.renderer.begin((group(0), group(1, .3)), ANCHOR, 1.)
        self.renderer.advance(1.19)
        staged = self.renderer.staging[1]['model_id']
        self.runtime.fail_show_model = staged
        self.renderer.visible = True
        for now in (1.21, 1.24, 1.27, 1.31):
            ready = self.renderer.advance(now)
        self.assertFalse(ready)
        self.assertEqual(set(old), set(self.runtime.models))
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.assertEqual({}, self.renderer.staging)

    def test_later_uniform_failure_cleans_partial_staged_model(self):
        self.settle((group(),), 0.)
        self.runtime.fail_uniform_index = 2
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual(1, len(self.runtime.models))
        self.assertIn(2, self.runtime.removed)

    def test_creations_are_bounded_and_cancel_discards_unallocated_groups(self):
        self.renderer.CREATIONS_PER_FRAME = 2
        self.renderer.begin(tuple(group(key) for key in range(4)), ANCHOR, 0.)
        self.assertEqual(0, self.runtime.serial)
        self.assertFalse(self.renderer.advance(.01))
        self.assertEqual(2, self.runtime.serial)
        self.assertTrue(all(self.runtime.hidden(model) for model in self.runtime.models))
        self.renderer.begin((), ANCHOR, .02)
        self.assertEqual({}, self.runtime.models)
        self.assertTrue(self.renderer.advance(.3))
        self.assertEqual(2, self.runtime.serial)

    def test_failed_anchor_move_restores_models_already_moved(self):
        self.settle((group(0), group(1)), 0.)
        old_positions = dict(self.runtime.positions)
        self.runtime.fail_move_model = self.renderer.active[1]['model_id']
        self.assertFalse(self.renderer.follow((20., 74., 30.)))
        self.assertEqual(old_positions, self.runtime.positions)
        self.assertEqual(ANCHOR, self.renderer.anchor)
        self.assertTrue(all(record['anchor'] == ANCHOR for record in self.renderer.active.values()))

    def test_native_pose_and_dimension_must_be_explicit_and_finite(self):
        for dimension, scale, rotation in ((True, (1.,) * 3, (0.,) * 3),
                (0, (0., 1., 1.), (0.,) * 3), (0, (1.,) * 3, (float('nan'), 0., 0.))):
            with self.assertRaises(ValueError):
                WorldLiquidRenderer(self.runtime, 4, dimension, scale, rotation)


if __name__ == '__main__':
    unittest.main()
