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

    def pinch(self):
        self.tracker.touch_mode = lambda: True
        self.tracker.props['onPinch'] = self.record('onPinch')
        self.tracker.props['screenHit'] = lambda p: p[0] < 500
        self.down()
        self.tracker.move({'TouchId':0,'TouchPosX':110,'TouchPosY':210})
        self.tracker.down({'TouchId':1,'TouchPosX':210,'TouchPosY':210})

    def test_pinch_tracks_latest_contacts_and_releases_without_edit(self):
        for first in (0, 1):
            self.events[:] = []
            self.pinch()
            self.assertEqual(((110,210),(210,210)), self.events[-1][1]['points'])
            self.assertEqual('start', self.events[-1][1]['phase'])
            self.tracker.move({'TouchId':1,'TouchPosX':250,'TouchPosY':230})
            self.assertEqual(((110,210),(250,230)), self.events[-1][1]['points'])
            release_pointers(self.host, {'TouchId':first})
            self.assertTrue(self.tracker.pressed)
            self.tracker.up({'TouchId':first})  # duplicate local up
            self.tracker.move({'TouchId':1-first,'TouchPosX':300,'TouchPosY':250})
            self.tracker.move_out({'TouchId':1-first, 'TouchEvent':6})
            self.assertTrue(self.tracker.pressed)
            self.tracker.up({'TouchId':1-first, 'TouchEvent':0})
            self.assertEqual('end', self.events[-1][1]['phase'])
            self.assertFalse(any(name=='onUp' for name,args in self.events))
            self.assertFalse(self.tracker.pressed)
            self.assertFalse(self.host._projection_pointers)

    def test_pinch_pair_replacement_and_ambiguous_capture_loss(self):
        self.pinch()
        self.tracker.down({'TouchId':2,'TouchPosX':310,'TouchPosY':210})
        self.tracker.cancel({'TouchId':0})
        self.assertEqual('start', self.events[-1][1]['phase'])
        self.assertEqual(((210,210),(310,210)), self.events[-1][1]['points'])
        release_pointers(self.host,{})
        self.assertFalse(self.tracker.pressed)
        self.assertEqual('onCancel',self.events[-1][0])

    def test_second_finger_on_navigation_does_not_steal_viewport(self):
        self.tracker.touch_mode=lambda: True
        self.tracker.props['onPinch']=self.record('onPinch')
        self.tracker.props['screenHit']=lambda p:p[0]<500
        self.down()
        self.tracker.screen_down({'TouchId':1},(550,200))
        self.tracker.cancel({'TouchId':1})
        self.assertFalse(self.tracker.pinching)
        self.assertTrue(self.tracker.pressed)
        self.tracker.up({'TouchId':0})
        self.assertEqual('onUp',self.events[-1][0])

    def test_second_contact_global_and_local_down_deduplicate(self):
        self.pinch()
        count=len(self.events)
        self.tracker.screen_down({'TouchId':1},(210,210))
        self.tracker.down({'TouchId':1,'TouchPosX':210,'TouchPosY':210})
        self.assertEqual(count,len(self.events))
        self.tracker.cancel({})
        self.assertFalse(self.tracker.contacts)

    def test_android_second_finger_move_without_down_starts_pinch(self):
        self.tracker.touch_mode = lambda: True
        self.tracker.props.update(onPinch=self.record('onPinch'),
                                  screenHit=lambda point: point[0] < 500)
        self.down()
        self.tracker.move({'TouchId': 0, 'TouchEvent': 4,
                           'TouchPosX': 110, 'TouchPosY': 200})
        self.tracker.move({'TouchId': 1, 'TouchEvent': 4,
                           'TouchPosX': 210, 'TouchPosY': 200})
        self.assertTrue(self.tracker.pinching)
        self.tracker.move({'TouchId': 1, 'TouchEvent': 4,
                           'TouchPosX': 310, 'TouchPosY': 200})
        self.assertEqual(((110, 200), (310, 200)), self.events[-1][1]['points'])
        self.tracker.up({'TouchId': 0})
        self.tracker.touch_finished()  # No individual up for the other finger.
        self.tracker.touch_finished()
        self.assertFalse(self.tracker.pressed)
        self.assertFalse(self.tracker.contacts)
        self.assertFalse(any(name == 'onUp' for name, args in self.events))
        self.assertEqual(1, sum(name == 'onPinch' and args['phase'] == 'end'
                                for name, args in self.events))

    def test_android_local_second_move_outside_viewport_does_not_capture(self):
        self.tracker.touch_mode = lambda: True
        self.tracker.props.update(onPinch=self.record('onPinch'),
                                  screenHit=lambda point: point[0] < 500)
        self.down()
        self.tracker.move({'TouchId': 1, 'TouchEvent': 4,
                           'TouchPosX': 550, 'TouchPosY': 200})
        self.assertFalse(self.tracker.pinching)
        self.assertNotIn(1, self.tracker.contacts)

    def test_aggregate_touch_release_does_not_consume_single_finger_click(self):
        self.tracker.touch_mode = lambda: True
        self.down()
        self.tracker.touch_finished()
        self.tracker.up({'TouchId': 0})
        self.assertEqual(['onDown', 'onUp'], [name for name, args in self.events])

    def down(self):
        self.tracker.down({'TouchPosX': 100, 'TouchPosY': 200, 'TouchId': 0})

    def test_phone_touch_ignores_desktop_cursor_and_does_not_double_release(self):
        self.tracker.touch_mode=lambda: True
        self.down()
        self.assertIsNone(self.tracker.origin)
        self.assertFalse(self.frames)
        self.tracker.leave({});self.tracker.move_out({})
        self.assertTrue(self.tracker.pressed)
        self.tracker.move({'TouchPosX':140,'TouchPosY':240,'TouchId':0})
        self.tracker.up({'TouchPosX':140,'TouchPosY':240,'TouchId':0})
        self.tracker.up({})
        self.assertEqual(1,sum(n=='onUp' for n,a in self.events))
        self.assertEqual(140,self.events[-1][1]['TouchPosX'])
        self.assertEqual('touch',self.events[-1][1]['pointerKind'])

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

    def test_touch_move_out_retains_capture_until_screen_exit(self):
        self.tracker.touch_mode = lambda: True
        self.down()
        self.tracker.move({'TouchPosX': 140, 'TouchPosY': 240, 'TouchId': 0})
        self.tracker.move_out({'TouchEvent': 6, 'TouchId': 1})
        self.assertTrue(self.tracker.pressed)
        self.tracker.move_out({'TouchEvent': 6, 'TouchId': 0})
        self.assertTrue(self.tracker.pressed)
        self.tracker.move_out({'TouchEvent': 7, 'TouchId': 0})
        self.tracker.up({'TouchId': 0})
        self.tracker.move({'TouchPosX': 150, 'TouchPosY': 250, 'TouchId': 0})
        self.assertEqual(['onDown', 'onMove', 'onCancel'], [name for name, args in self.events])
        self.assertFalse(self.tracker.pressed)
        self.assertFalse(self.host._projection_pointers)

    def test_native_second_touch_moves_without_local_button_move(self):
        self.tracker.touch_mode = lambda: True
        self.tracker.props.update(onPinch=self.record('onPinch'), globalCapture=True,
                                  screenHit=lambda p: p[0] < 500)
        for identity, x in ((0, 100), (1, 200)):
            self.tracker.native_touch({'TouchId':identity, 'TouchEvent':1,
                                       'TouchPosX':x, 'TouchPosY':200})
        self.assertTrue(self.tracker.pinching)
        self.tracker.native_touch({'TouchId':1,'TouchEvent':4,'TouchPosX':300,'TouchPosY':200})
        self.assertEqual(((100,200),(300,200)), self.events[-1][1]['points'])
        self.tracker.native_touch({'TouchId':1,'TouchEvent':6,'TouchPosX':510,'TouchPosY':200})
        self.assertTrue(self.tracker.pinching)
        self.tracker.native_touch({'TouchId':1,'TouchEvent':0})
        self.tracker.native_touch({'TouchId':0,'TouchEvent':0})
        self.assertFalse(self.tracker.pressed)
        self.assertFalse(any(name == 'onUp' for name, args in self.events))

    def test_native_move_code_two_zooms_when_input_mode_is_stale(self):
        self.tracker.props.update(onPinch=self.record('onPinch'), globalCapture=True,
                                  screenHit=lambda point: point[0] < 500)
        for identity, x in ((0, 100), (1, 200)):
            self.tracker.native_touch({'TouchId': identity, 'TouchEvent': 1,
                                       'TouchPosX': x, 'TouchPosY': 200})
        self.assertTrue(self.tracker.pinching)
        self.assertTrue(self.tracker.touch)
        self.tracker.native_touch({'TouchId': 1, 'TouchEvent': 2,
                                   'TouchPosX': 300, 'TouchPosY': 200})
        self.assertEqual(((100, 200), (300, 200)), self.events[-1][1]['points'])
        self.tracker.native_touch({'TouchId': 0, 'TouchEvent': 0})
        self.tracker.native_touch({'TouchId': 1, 'TouchEvent': 0})
        self.assertFalse(self.tracker.pressed)

    def test_native_secondary_contact_does_not_start_over_toolbar(self):
        self.pinch()
        self.tracker.native_touch({'TouchId':2,'TouchEvent':4,'TouchPosX':550,'TouchPosY':20})
        self.tracker.native_touch({'TouchId':2,'TouchEvent':4,'TouchPosX':250,'TouchPosY':200})
        self.assertNotIn(2, self.tracker.contacts)
        self.tracker.native_touch({'TouchEvent':7})
        self.assertFalse(self.tracker.pressed)

    def test_touch_up_then_move_out_keeps_exactly_one_tap(self):
        self.tracker.touch_mode = lambda: True
        self.down()
        self.tracker.up({'TouchPosX': 100, 'TouchPosY': 200, 'TouchId': 0})
        self.tracker.move_out({'TouchEvent': 6, 'TouchId': 0})
        self.assertEqual(['onDown', 'onUp'], [name for name, args in self.events])

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
        self.assertEqual(('onMove', {'TouchPosX':310, 'TouchPosY':250, 'TouchId':0, 'pointerKind':'mouse'}), self.events[-1])
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
        release_pointers(self.host, {'TouchId': 0, 'TouchPosX': 102, 'TouchPosY': 204, 'pointerKind':'mouse'})
        self.assertEqual(('onUp', {'TouchId': 0, 'TouchPosX': 102, 'TouchPosY': 204, 'pointerKind':'mouse'}), self.events[-1])
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
