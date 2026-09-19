"""Replacement lifecycle: retain the old image, discard stale work, avoid idle renders."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.preview import PreviewBuffer


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.preview = PreviewBuffer()
        self.draws, self.shows = [], []
        self.fail = False

    def draw(self, *args):
        self.draws.append(args)
        return not self.fail

    def show(self, *args):
        self.shows.append(args)

    def tick(self, name, now, pose=(1., -65., 35.)):
        self.preview.update(name, pose, now, self.draw, self.show)

    def settle(self, name, start=0.):
        for t in (0., .04, .08):
            self.tick(name, start + t)

    def test_replacement_keeps_front_until_render_opportunities_elapsed(self):
        self.settle('old')
        old = self.preview.front
        self.shows[:] = []
        self.tick('new', .1)
        self.tick('new', .14)
        self.assertEqual(self.preview.front, old)
        self.assertNotIn((old, False, False), self.shows)
        self.assertFalse(self.preview.ready('new'))
        self.tick('new', .18)
        self.assertTrue(self.preview.ready('new'))
        self.assertEqual(self.shows[-2:], [(1 - old, True, True), (old, False, False)])

    def test_idle_does_not_submit_and_orbit_does_not_reload_geometry(self):
        self.settle('old')
        self.draws[:] = []
        self.tick('old', .2)
        self.assertEqual(self.draws, [])
        self.tick('old', .3, (1.1, -45., 50.))
        self.assertEqual(len(self.draws), 1)
        self.assertEqual(self.draws[0][1], 'old')

    def test_promotion_resubmits_after_visibility_and_depth_without_camera_motion(self):
        self.settle('old')
        old_count = len(self.draws)
        self.tick('new', .1)
        self.tick('new', .14)
        self.tick('new', .18)
        self.assertEqual(old_count+2, len(self.draws))
        self.assertEqual('new', self.draws[-1][1])
        self.tick('new', .2)
        self.assertEqual(old_count+2, len(self.draws))

    def test_superseded_and_failed_replacement_never_becomes_front(self):
        self.settle('old')
        self.tick('stale', .1)
        self.fail = True
        for now in (.2, .3, .4):
            self.tick('latest', now)
        self.assertEqual(self.preview.names[self.preview.front], 'old')
        self.fail = False
        self.settle('latest', .7)
        self.assertTrue(self.preview.ready('latest'))

    def test_empty_scene_clears_both_surfaces_and_undo_cancels_pending(self):
        self.settle('old')
        self.tick('new', .1)
        self.tick('old', .2)
        self.assertFalse(self.preview.ready('old'))
        self.tick('old', .22)
        self.assertTrue(self.preview.ready('old'))
        self.tick(None, .3)
        self.assertTrue(self.preview.ready(None))
        self.assertEqual(self.preview.names, [None, None])

    def test_rapid_replacement_and_orbit_never_overwrite_warming_surface(self):
        self.settle('old')
        self.tick('stale', .1)
        self.draws[:] = []
        self.tick('latest', .12, (2., -40., 60.))
        self.tick('latest', .14, (2., -40., 70.))
        self.assertTrue(all(name == 'old' for slot, name, pose in self.draws))
        self.assertFalse(self.preview.ready('latest'))
        self.settle('latest', .2)
        self.assertTrue(self.preview.ready('latest'))

    def test_failed_native_submission_is_throttled(self):
        self.fail = True
        for frame in range(60):
            self.tick('bad', frame / 60.)
        self.assertLessEqual(len(self.draws), 4)
