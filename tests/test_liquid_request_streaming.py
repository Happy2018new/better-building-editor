"""Real renderer cold submissions and replacement readiness under a frame budget."""
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.liquid_viewport import LiquidControls, LiquidView
from tests.test_liquid_render import POSE, group
from tests.test_liquid_viewport import Control, RecordedModel


class LiquidRequestStreamingTests(unittest.TestCase):
    def owner(self, count=4, budget=1):
        registry = {}
        for key in range(count):
            registry[key] = {
                'dolls': [SimpleNamespace(current=Control(100 + 2 * key + slot)) for slot in range(2)],
                'surfaces': [SimpleNamespace(current=Control(200 + 2 * key + slot)) for slot in range(2)]}
        owner = LiquidControls(registry, RecordedModel(), request_starts_per_frame=budget)
        return owner, {key: group(key=key) for key in registry}

    def update(self, owner, groups, now, pose=POSE, clipped=False):
        return owner.update(groups, lambda origin: LiquidView((0., 0.), (100., 100.), -4., clipped),
                            lambda view: pose, (0., 0.), now)

    def submissions(self, owner):
        return sum(len(ref.current.doll.calls) for entry in owner.registry.values() for ref in entry['dolls'])

    def finish(self, owner, groups, start=0.):
        rows = []
        for frame in range(30):
            before = self.submissions(owner)
            ready = self.update(owner, groups, start + frame / 60.)
            rows.append(self.submissions(owner) - before)
            if ready:
                return rows
        self.fail('Cold request never finished')

    def test_cold_uploads_are_nonzero_spread_and_complete_without_duplicate_submissions(self):
        owner, groups = self.owner(count=8)
        rows = self.finish(owner, groups)
        self.assertEqual(8, sum(rows))
        self.assertEqual([1] * 8, rows[:8])
        self.assertTrue(all(value <= 1 for value in rows))
        self.assertLessEqual(len(rows), 14)  # Eight starts plus native settle delay.
        self.assertTrue(all(entry['renderer'].pending is None for entry in owner.registry.values()))

    def test_default_owner_retains_simultaneous_cold_start_behavior(self):
        owner, groups = self.owner(budget=None)
        self.assertFalse(self.update(owner, groups, 0.))
        self.assertEqual(4, self.submissions(owner))

    def test_replacement_keeps_each_old_front_visible_until_its_incoming_bank_publishes(self):
        owner, groups = self.owner(count=8)
        self.finish(owner, groups)
        old = {key: (entry['renderer'].front, entry['renderer'].ids[entry['renderer'].front])
               for key, entry in owner.registry.items()}
        replacement = {key: group(key=key, height=.3) for key in groups}
        for frame in range(18):
            before = self.submissions(owner)
            ready = self.update(owner, replacement, 1. + frame / 60.)
            self.assertLessEqual(self.submissions(owner) - before, 1)
            for key, entry in owner.registry.items():
                renderer = entry['renderer']
                if renderer.front == old[key][0]:
                    self.assertTrue(renderer.visible[old[key][0]])
                    self.assertEqual(old[key][1], renderer.ids[renderer.front])
            if ready:
                break
        self.assertTrue(ready)
        self.assertEqual(16, self.submissions(owner))

    def test_continuously_superseded_first_group_cannot_starve_other_cold_requests(self):
        owner, groups = self.owner()
        for frame in range(4):
            groups[0] = group(key=0, height=.3 + frame * .1)
            self.update(owner, groups, frame / 60.)
        self.assertTrue(all(entry['renderer'].pending is not None for key, entry in owner.registry.items() if key))
        self.assertEqual(4, self.submissions(owner))

    def test_rejected_native_start_consumes_budget_and_latched_failure_does_not_block_tail(self):
        owner, groups = self.owner()
        owner.registry[0]['dolls'][1].current.doll.submit_ok = False
        self.update(owner, groups, 0.)
        self.assertEqual(1, self.submissions(owner))
        self.update(owner, groups, .02)
        self.assertEqual(2, self.submissions(owner))
        self.assertIsNotNone(owner.registry[1]['renderer'].pending)

    def test_clipping_and_disappearance_cancel_queued_work_without_starting_it(self):
        owner, groups = self.owner()
        self.update(owner, groups, 0.)
        self.assertTrue(self.update(owner, groups, .02, clipped=True))
        self.assertEqual(1, self.submissions(owner))
        self.assertTrue(all(entry['renderer'].pending is None for entry in owner.registry.values()))
        self.update(owner, {}, .04)
        self.assertEqual(1, self.submissions(owner))
        self.assertTrue(all(not any(entry['renderer'].visible) for entry in owner.registry.values()))

    def test_pose_and_depth_updates_of_published_fronts_are_not_queued_behind_cold_work(self):
        owner, groups = self.owner()
        self.finish(owner, groups)
        replacement = {key: group(key=key, height=.3) for key in groups}
        pose = (POSE[0], POSE[1], 15., POSE[3])
        self.update(owner, replacement, 1., pose=pose)
        for entry in owner.registry.values():
            renderer = entry['renderer']
            self.assertEqual(pose, renderer.poses[renderer.front])
        # The cold-start budget deliberately does not claim a bound on live orbit submissions.
        self.assertEqual(9, self.submissions(owner))

    def test_budget_rejects_invalid_values_and_invalidation_releases_cursor(self):
        for value in (0, -1, True, 1.5, '1'):
            with self.assertRaises(ValueError):
                self.owner(budget=value)
        owner, groups = self.owner(budget=2)
        self.update(owner, groups, 0.)
        self.assertEqual(2, self.submissions(owner))
        self.assertIsNotNone(owner.last_started_entry)
        owner.invalidate()
        self.assertIsNone(owner.last_started_entry)
        owner.close()
        self.assertFalse(self.update(owner, groups, 1.))


if __name__ == '__main__':
    unittest.main()
