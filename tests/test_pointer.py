import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.pointer import PointerTracker, release_pointers


class PointerTests(unittest.TestCase):
    def setUp(self):
        self.frames = []
        self.events = []
        self.pos = (20, 30)
        self.host = SimpleNamespace(
            pyreact_register_animation_frame=lambda slot: self.frames.append(slot),
            pyreact_unregister_animation_frame=lambda slot: self.frames.remove(slot) if slot in self.frames else None)
        self.tracker = PointerTracker(self.host, None, SimpleNamespace(GetMousePosition=lambda: self.pos))
        self.tracker.props = {name: self.record(name) for name in ('onDown', 'onUp', 'onMove', 'onCancel', 'onLeave')}

    def record(self, name):
        return lambda args: self.events.append((name, dict(args)))

    def down(self):
        self.tracker.down({'TouchPosX': 100, 'TouchPosY': 200, 'TouchId': 0})

    def test_global_release_finishes_lost_local_up_exactly_once(self):
        for global_first in (True, False):
            self.events[:] = []
            self.down()
            self.pos = (30, 40)
            if global_first:
                release_pointers(self.host, {'TouchId': -1})
            self.tracker.up({})
            release_pointers(self.host, {})
            self.assertEqual(1, sum(name == 'onUp' for name, args in self.events))
            self.assertFalse(self.tracker.pressed)
            self.assertFalse(self.frames)
            self.assertFalse(self.host._projection_pointers)
            count = len(self.events)
            self.pos = (90, 90)
            self.tracker.tick(0)
            self.tracker.move({'TouchPosX': 90, 'TouchPosY': 90})
            self.assertEqual(count, len(self.events))

    def test_mouse_leave_cancels_instead_of_clicking_and_reentry_is_idle(self):
        self.down()
        self.tracker.leave({})
        self.tracker.enter({})
        release_pointers(self.host, {})
        self.assertEqual(['onDown', 'onCancel', 'onLeave'], [n for n, args in self.events])
        self.assertFalse(self.frames)

    def test_scrollbar_capture_tracks_outside_rail_until_global_release(self):
        self.tracker.props['retainCapture'] = True
        self.down()
        self.tracker.move_out({})
        self.tracker.leave({})
        self.pos = (230, 80)
        self.tracker.tick(0)
        self.assertTrue(self.tracker.pressed)
        self.assertEqual(('onMove', {'TouchPosX':310, 'TouchPosY':250, 'TouchId':0}), self.events[-1])
        release_pointers(self.host, {})
        self.assertFalse(self.frames)
        self.assertFalse(self.tracker.pressed)
        count = len(self.events)
        self.pos = (300, 150)
        self.tracker.tick(0)
        self.assertEqual(count, len(self.events))

    def test_retained_capture_still_cancels_when_mouse_or_control_is_lost(self):
        self.tracker.props['retainCapture'] = True
        self.down(); self.pos = None
        self.tracker.tick(0)
        self.assertFalse(self.tracker.pressed)
        self.assertFalse(self.frames)

    def test_capture_loss_and_duplicate_down_do_not_leak_pollers(self):
        self.down()
        self.down()
        self.assertEqual(1, len(self.frames))
        self.pos = None
        self.tracker.tick(0)
        self.assertFalse(self.tracker.pressed)
        self.assertFalse(self.frames)
        self.assertEqual(2, sum(n == 'onCancel' for n, args in self.events))

    def test_touch_release_is_scoped_to_contact_and_uses_release_position(self):
        self.pos = None
        self.down()
        self.tracker.move_out({})
        self.tracker.leave({})
        self.assertTrue(self.tracker.pressed)
        release_pointers(self.host, {'TouchId': 1})
        self.assertTrue(self.tracker.pressed)
        release_pointers(self.host, {'TouchId': 0, 'TouchPosX': 102, 'TouchPosY': 204})
        self.assertEqual(('onUp', {'TouchId': 0, 'TouchPosX': 102, 'TouchPosY': 204}), self.events[-1])
        self.assertFalse(self.host._projection_pointers)

    def test_global_press_recovers_missing_native_down_without_double_edit(self):
        self.tracker.props['globalCapture'] = True
        self.tracker.enter({})
        for native_first in (False, True):
            self.events[:] = []
            if native_first:
                self.down()
            self.tracker.screen_down({}, (100, 200))
            if not native_first:
                self.down()
            release_pointers(self.host, {})
            self.tracker.up({})
            self.assertEqual(['onDown', 'onUp'], [n for n, unused in self.events])
        self.events[:] = []
        for unused in range(40):
            self.tracker.screen_down({}, (100, 200))
            release_pointers(self.host, {})
        self.assertEqual(40, sum(n == 'onUp' for n, unused in self.events))

    def test_global_press_respects_native_hit_testing_and_disabled_view(self):
        self.tracker.props['globalCapture'] = True
        self.tracker.screen_down({}, (100, 200))
        self.assertFalse(self.events)
        self.tracker.enter({}); self.tracker.props['enabled'] = False
        self.tracker.screen_down({}, (100, 200))
        self.assertFalse(self.events)
        self.tracker.props['enabled'] = True
        self.tracker.screen_down({}, None)
        self.assertFalse(self.events)


if __name__ == '__main__':
    unittest.main()
