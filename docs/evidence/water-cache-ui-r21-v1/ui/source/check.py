"""Exercise the candidate inside the existing renderer lifetime tests, offline."""
import os
from pathlib import Path
import sys
import unittest

os.environ['OPENBLAS_NUM_THREADS'] = '1'
ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / 'tests')]
from tests.test_liquid_render import SkeletonLiquidTests, Doll, Model, group, POSE
from projection.liquid_render import SkeletonLiquidRenderer
from projection.liquid_transport import with_preview_distance
from candidate import entity_draw_pose


class EntityDrawDoll(Doll):
    def __init__(self):
        super().__init__()
        self.native_calls = []
        self.entity_ok = True

    def RenderSkeletonModel(self, params):
        self.native_calls.append(('skeleton', dict(params)))
        return super().RenderSkeletonModel(params)

    def RenderEntity(self, params):
        self.native_calls.append(('entity', dict(params)))
        return self.entity_ok


class CandidateRenderer(SkeletonLiquidRenderer):
    _render_pose = entity_draw_pose


class ExistingLifecycleTests(SkeletonLiquidTests):
    def setUp(self):
        self.dolls = (EntityDrawDoll(), EntityDrawDoll())
        self.model, self.shown = Model(), {}
        self.renderer = CandidateRenderer(self.dolls, self.model, self.shown.__setitem__)


class SubmissionCandidateTests(unittest.TestCase):
    def setUp(self):
        self.dolls = (EntityDrawDoll(), EntityDrawDoll())
        self.model, self.shown = Model(), {}
        self.renderer = CandidateRenderer(self.dolls, self.model, self.shown.__setitem__)

    def test_exact_model_assignment_then_entity_draw_with_identical_pose_and_depth(self):
        value = with_preview_distance(group(), -4.)
        self.assertTrue(self.renderer._render_pose(1, value, POSE))
        skeleton, entity = self.dolls[1].native_calls
        self.assertEqual(('skeleton', 'entity'), (skeleton[0], entity[0]))
        assigned, drawn = skeleton[1], entity[1]
        self.assertEqual(value.model_name, assigned.pop('skeleton_model_name'))
        self.assertEqual('minecraft:cow', drawn.pop('entity_identifier'))
        self.assertEqual(assigned, drawn)
        self.assertEqual(-50, drawn['render_depth'])
        self.assertEqual([], self.model.calls)
        self.assertEqual(-1, self.dolls[1].model_id)
        self.assertEqual([], self.dolls[0].native_calls)
        self.assertEqual(with_preview_distance(group(), -4.), value)

    def test_rejected_skeleton_does_not_submit_entity_draw(self):
        self.dolls[1].submit_ok = False
        self.assertFalse(self.renderer._render_pose(1, group(), POSE))
        self.assertEqual(['skeleton'], [row[0] for row in self.dolls[1].native_calls])

    def test_rejected_entity_draw_is_latched_and_preserves_published_bank(self):
        old = group(height=.7)
        self.renderer.update(old, POSE, 0.)
        self.dolls[1].model_id = 1
        for now in (.03, .06, .09):
            self.renderer.update(old, POSE, now)
        self.assertEqual(1, self.renderer.front)
        self.assertEqual(old, self.renderer.groups[1])
        self.dolls[0].entity_ok = False
        incoming = group(height=.3)
        self.assertFalse(self.renderer.update(incoming, POSE, 1.))
        calls = len(self.dolls[0].native_calls)
        for tick in range(10):
            self.assertFalse(self.renderer.update(incoming, POSE, 1.1 + tick * .1))
        self.assertEqual(calls, len(self.dolls[0].native_calls))
        self.assertEqual(1, self.renderer.front)
        self.assertEqual(old, self.renderer.groups[1])
        self.assertTrue(self.shown[1])
        self.assertFalse(self.shown[0])

    def test_shared_renderer_stays_on_skeleton_api(self):
        renderer = SkeletonLiquidRenderer(self.dolls, self.model, self.shown.__setitem__)
        self.assertTrue(renderer._render_pose(1, group(), POSE))
        self.assertEqual(['skeleton'], [row[0] for row in self.dolls[1].native_calls])

    def test_preview_distance_uses_original_tag134_uniform_path_without_entity_resubmit(self):
        value = with_preview_distance(group(), -4.)
        self.renderer.update(value, POSE, 0.)
        self.dolls[1].model_id = 1
        for now in (.03, .06, .09):
            self.renderer.update(value, POSE, now)
        calls = len(self.dolls[1].native_calls)
        changed = with_preview_distance(group(), -3.)
        self.assertTrue(self.renderer.update(changed, POSE, 1.))
        self.assertEqual((1, 4, changed.uniforms[3]), self.model.calls[-1])
        self.assertEqual(134, int(changed.uniforms[3][0]) & 255)
        self.assertEqual(1, self.renderer.ids[1])
        self.assertEqual(calls, len(self.dolls[1].native_calls))


if __name__ == '__main__':
    unittest.main()
