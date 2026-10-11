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
        self.assertFalse(self.renderer.update(value, (.15, -45., 0., 0.), 1.))
        self.dolls[0].model_id = 5
        for now in (1.03, 1.06, 1.09):
            ready = self.renderer.update(value, (.15, -45., 0., 0.), now)
        self.assertTrue(ready)
        self.assertEqual([5] * 4, [call[0] for call in self.model.calls[-4:]])

    def test_pose_changes_while_pending_restart_hidden_slot_and_keep_front_untouched(self):
        value = group()
        self.assertTrue(self.settle(value, 0., 1))
        old_calls = len(self.dolls[1].calls)
        second_pose, final_pose = (.15, -45., 0., 0.), (.15, -35., 0., 0.)
        self.renderer.update(value, second_pose, 1.)
        self.dolls[0].model_id = 2
        self.renderer.update(value, second_pose, 1.03)
        self.renderer.update(value, final_pose, 1.04)
        self.assertEqual((value, final_pose), self.renderer.pending)
        self.assertEqual(old_calls, len(self.dolls[1].calls))
        self.assertEqual({0: True, 1: True}, self.shown)
        for now in (1.07, 1.10, 1.13):
            self.renderer.update(value, final_pose, now)
        self.assertEqual(final_pose, self.renderer.poses[self.renderer.front])

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


class Actor:
    def __init__(self, runtime, entity):
        self.runtime, self.entity = runtime, entity
        self.attached = None
        self.hidden = True
        self.uniforms = {}

    def SetNotRenderAtAll(self, value):
        if not value and self.entity == self.runtime.fail_show_entity:
            return False
        self.hidden = value
        return True

    def AddActorBlockGeometry(self, name, offset, rotation):
        if not self.runtime.attach_ok:
            return False
        self.attached, self.offset, self.rotation = name, offset, rotation
        return True

    def DeleteActorBlockGeometry(self, name):
        self.runtime.removed.append((self.entity, name))
        self.attached = None
        return self.runtime.delete_ok

    def EnableActorBlockGeometryTransparent(self, unused_name, unused_value):
        return True

    def SetActorBlockGeometryTransparency(self, unused_name, unused_value):
        return True

    def SetEntityExtraUniforms(self, index, value):
        if not self.runtime.uniforms_ok or index == self.runtime.fail_uniform_index:
            return False
        self.uniforms[index] = value
        self.runtime.uniform_calls.append((self.entity, index, value))
        return True

    def SetActorBlockGeometryOffset(self, unused_name, offset):
        self.offset = offset
        return True

    def SetPosForClientEntity(self, value):
        self.runtime.positions[self.entity] = value
        return True


class Runtime:
    def __init__(self):
        self.factory = self.system = self
        self.alive = True
        self.actors, self.positions = {}, {}
        self.destroyed, self.removed, self.uniform_calls = [], [], []
        self.attach_ok = self.uniforms_ok = self.delete_ok = True
        self.destroy_ok = True
        self.fail_show_entity = self.fail_uniform_index = None
        self.serial = self.peak_live = 0

    def CreateClientEntityByTypeStr(self, identifier, position, unused_rotation):
        assert identifier == b'modern_projection:anchor'
        self.serial += 1
        self.actors[self.serial] = Actor(self, self.serial)
        self.positions[self.serial] = position
        self.peak_live = max(self.peak_live, len(self.actors))
        return self.serial

    def CreateActorRender(self, entity):
        return self.actors[entity]

    def CreatePos(self, entity):
        return self.actors[entity]

    def DestroyClientEntity(self, entity):
        if not self.destroy_ok:
            return False
        self.destroyed.append(entity)
        del self.actors[entity]
        del self.positions[entity]


class WorldLiquidTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Runtime()
        self.renderer = WorldLiquidRenderer(self.runtime, 4)

    def settle(self, groups, now):
        self.assertTrue(self.renderer.begin(groups, ANCHOR, now))
        for delay in (.19, .21, .24, .27, .31):
            ready = self.renderer.advance(now + delay)
        self.assertTrue(ready)

    def test_actor_delay_and_warmup_keep_previous_generation_visible(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['entity']
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.19))
        self.assertFalse(self.renderer.advance(1.21))
        self.assertFalse(self.runtime.actors[old].hidden)
        staged = self.renderer.staging[0]['entity']
        self.assertTrue(self.runtime.actors[staged].hidden)
        self.assertEqual(4, len(self.runtime.actors[staged].uniforms))
        for now in (1.24, 1.27, 1.31):
            self.renderer.advance(now)
        self.assertEqual([old], self.runtime.destroyed)
        self.assertFalse(self.runtime.actors[staged].hidden)

    def test_many_replacements_never_exceed_two_bounded_generations_and_cleanup_all(self):
        for iteration in range(100):
            self.settle(tuple(group(key, iteration / 100.) for key in range(4)), float(iteration))
        self.assertEqual(8, self.runtime.peak_live)
        self.assertEqual(4, len(self.runtime.actors))
        self.assertTrue(self.renderer.close())
        self.assertTrue(self.renderer.close())
        self.assertEqual({}, self.runtime.actors)
        self.assertEqual(400, len(self.runtime.removed))

    def test_unchanged_groups_and_anchor_motion_reuse_owned_instances_and_payload(self):
        groups = (group(),)
        self.settle(groups, 0.)
        calls = len(self.runtime.uniform_calls)
        self.assertTrue(self.renderer.begin(groups, (11., 65., 21.), 1.))
        self.assertEqual(1, self.runtime.serial)
        self.assertEqual(calls, len(self.runtime.uniform_calls))
        actor = self.renderer.active[0]['entity']
        self.assertEqual((11., 65., 21.), self.runtime.positions[actor])
        self.assertEqual((6.5, -65., 12.5), self.runtime.actors[actor].offset)

    def test_failed_attach_preserves_active_and_cleans_staging(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['entity']
        self.runtime.attach_ok = False
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual([old], list(self.runtime.actors))
        self.assertEqual({}, self.renderer.staging)
        self.assertIn('attach', self.renderer.error)
        self.assertFalse(self.runtime.actors[old].hidden)

    def test_failed_payload_detaches_created_geometry_and_preserves_active(self):
        self.settle((group(height=.7),), 0.)
        old = self.renderer.active[0]['entity']
        self.runtime.uniforms_ok = False
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        staged = self.renderer.staging[0]['entity']
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual([old], list(self.runtime.actors))
        self.assertEqual((staged, 'native_liquid_model'), self.runtime.removed[-1])

    def test_budget_rejection_and_duplicate_keys_leave_existing_pending_transaction(self):
        self.renderer.begin((group(),), ANCHOR, 0.)
        staged = self.renderer.staging[0]['entity']
        for groups in (tuple(group(key) for key in range(5)), (group(), group())):
            with self.assertRaises(ValueError):
                self.renderer.begin(groups, ANCHOR, .1)
        self.assertEqual(staged, self.renderer.staging[0]['entity'])
        self.assertEqual([], self.runtime.destroyed)

    def test_cancel_empty_hide_and_bridge_shutdown_cleanup_owned_actors(self):
        self.settle((group(),), 0.)
        self.assertTrue(self.renderer.set_visible(False))
        self.assertTrue(next(iter(self.runtime.actors.values())).hidden)
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        self.assertTrue(self.renderer.begin((), ANCHOR, 1.1))
        self.assertEqual({}, self.runtime.actors)
        self.renderer.begin((group(),), ANCHOR, 2.)
        self.runtime.alive = False
        self.assertFalse(self.renderer.advance(2.3))
        self.assertEqual({}, self.runtime.actors)

    def test_geometry_cleanup_failure_retains_ownership_and_retries_after_close(self):
        self.settle((group(),), 0.)
        self.runtime.delete_ok = False
        self.assertFalse(self.renderer.close())
        self.assertEqual(1, len(self.runtime.actors))
        self.assertEqual(1, len(self.renderer.retired))
        self.assertEqual(1, len(self.renderer.cleanup_errors))
        self.runtime.delete_ok = True
        self.assertTrue(self.renderer.advance(1.))
        self.assertEqual({}, self.runtime.actors)

    def test_destroy_failure_retains_detached_actor_until_retry(self):
        self.settle((group(),), 0.)
        self.runtime.destroy_ok = False
        self.assertFalse(self.renderer.close())
        self.assertEqual(1, len(self.renderer.retired))
        self.assertIsNone(next(iter(self.runtime.actors.values())).attached)
        self.runtime.destroy_ok = True
        self.assertTrue(self.renderer.retry_retired())
        self.assertEqual({}, self.runtime.actors)
        self.assertEqual(1, len(self.runtime.removed))

    def test_retired_actors_count_toward_budget_after_failed_replacements(self):
        self.renderer = WorldLiquidRenderer(self.runtime, 1)
        self.settle((group(height=.7),), 0.)
        self.runtime.delete_ok = False
        self.settle((group(height=.3),), 1.)
        self.assertEqual(1, len(self.renderer.retired))
        self.assertFalse(self.renderer.begin((group(height=.5),), ANCHOR, 2.))
        self.assertEqual(2, self.runtime.peak_live)
        self.assertEqual(2, len(self.runtime.actors))
        self.assertIn('Retired', self.renderer.error)
        self.runtime.delete_ok = True
        self.settle((group(height=.5),), 3.)
        self.assertEqual(1, len(self.runtime.actors))

    def test_middle_visibility_failure_rolls_back_old_actors_and_cleans_new(self):
        self.settle((group(0), group(1)), 0.)
        old = tuple(record['entity'] for record in self.renderer.active.values())
        self.renderer.set_visible(False)
        self.renderer.begin((group(0), group(1, .3)), ANCHOR, 1.)
        staged = self.renderer.staging[1]['entity']
        self.runtime.fail_show_entity = staged
        self.renderer.visible = True
        for now in (1.21, 1.24, 1.27, 1.31):
            ready = self.renderer.advance(now)
        self.assertFalse(ready)
        self.assertEqual(set(old), set(self.runtime.actors))
        self.assertTrue(all(actor.hidden for actor in self.runtime.actors.values()))
        self.assertEqual({}, self.renderer.staging)

    def test_later_uniform_failure_cleans_partial_staged_actor(self):
        self.settle((group(),), 0.)
        self.runtime.fail_uniform_index = 2
        self.renderer.begin((group(height=.3),), ANCHOR, 1.)
        staged = self.renderer.staging[0]['entity']
        self.assertFalse(self.renderer.advance(1.21))
        self.assertEqual(1, len(self.runtime.actors))
        self.assertIn((staged, 'native_liquid_model'), self.runtime.removed)


if __name__ == '__main__':
    unittest.main()
