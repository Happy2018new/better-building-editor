"""Sign diagnostics require consumed camera focus and real reversible controls."""
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_sign_visuals as tool


class Control:
    def __init__(self, visible):
        self.visible = visible
        self.writes = []

    def GetVisible(self):
        return self.visible

    def SetVisible(self, value):
        self.visible = value
        self.writes.append(value)


class Check:
    def __init__(self, consume=True, capture_error=False):
        self.consume = consume
        self.capture_error = capture_error
        self.controls = {'edge_control': Control(True), 'cursor_control': Control(False)}
        fibers = [SimpleNamespace(key=name, native_path=None, child_fibers=[
            SimpleNamespace(key=None, native_path=name+'_control', child_fibers=[])])
            for name in ('edge', 'cursor')]
        host = SimpleNamespace(_root_fiber=SimpleNamespace(key=None, native_path=None,
            child_fibers=fibers), GetBaseUIControl=self.controls.__getitem__)
        self.selection = [1]
        editor = SimpleNamespace(_selection_state=lambda cells: cells,
                                 _restore_selection=lambda cells: self.selection.clear())
        self.session = SimpleNamespace(editor=editor, box_anchor=None, focused=None,
            camera_focus_request=None, camera_pivot=(1.5, 1.5, 1.5), camera_pan=(0., 0.),
            scene_origin=(0, 0, 0), camera_pose=(35., 25., 1.), emit=lambda: None)
        self.session.locate_selected = lambda: setattr(self.session, 'camera_focus_request',
            tuple(value+.5 for value in self.session.focused))
        self.session.camera_view = lambda *pose: setattr(self.session, 'camera_pose', pose)
        self.namespace = {'s': self.session, 'json': json,
            'navigator': SimpleNamespace(top=SimpleNamespace(_host=host))}

    def run(self, code):
        exec(code, self.namespace)
        result = self.namespace['_result']
        return json.loads(result) if isinstance(result, str) else result

    def wait(self, label, predicate, current):
        if self.consume and self.session.camera_focus_request is not None:
            self.session.camera_pivot = tuple(self.session.camera_focus_request[i]
                - self.session.scene_origin[i] for i in range(3))
            self.session.camera_focus_request = None
            self.session.camera_pose = (35., 25., 7.)
        result = current()
        if not predicate(result):
            raise AssertionError(label)
        return result

    def capture(self, label):
        assert not any(control.GetVisible() for control in self.controls.values())
        if self.capture_error:
            raise RuntimeError('capture failed')
        return {'label': label}


class SignCaptureStateTests(unittest.TestCase):
    def test_matching_pivot_does_not_bypass_unconsumed_focus_request(self):
        with self.assertRaisesRegex(AssertionError, 'focus request consumed'):
            tool.center_editor(Check(consume=False), (1, 1, 1), {'editor': (0., 0., 3.)})

    def test_consumed_focus_uses_scene_origin_and_restores_declared_view(self):
        check = Check()
        check.session.scene_origin = (1, 0, 1)
        view = {'id': 'back', 'editor': (180., 0., 3.)}
        with patch.object(tool.time, 'sleep'):
            result = tool.center_editor(check, (1, 1, 1), view)
        self.assertEqual([.5, 1.5, .5], result['consumed']['pivot'])
        self.assertIsNone(result['consumed']['request'])
        self.assertEqual([180., 0., 3.], result['settled_pose'])
        self.assertEqual([], check.selection)
        self.assertIsNone(check.session.focused)

    def test_capture_hides_native_controls_and_restores_each_original_visibility(self):
        check = Check()
        shot = tool.capture_editor(check, 'sign_editor_shown', {'declared_view': 'front'})
        self.assertEqual({'edge', 'cursor'}, {row['key'] for row in shot['actual_hidden_controls']['overlays']})
        self.assertTrue(all(not row['after'] for row in shot['actual_hidden_controls']['overlays']))
        self.assertEqual([False, True], check.controls['edge_control'].writes)
        self.assertEqual([False, False], check.controls['cursor_control'].writes)

    def test_capture_failure_still_restores_real_controls(self):
        check = Check(capture_error=True)
        with self.assertRaisesRegex(RuntimeError, 'capture failed'):
            tool.capture_editor(check, 'sign_editor_shown', {})
        self.assertTrue(check.controls['edge_control'].GetVisible())
        self.assertFalse(check.controls['cursor_control'].GetVisible())

    def test_missing_overlay_witness_does_not_mutate_the_other_control(self):
        check = Check()
        check.namespace['navigator'].top._host._root_fiber.child_fibers.pop()
        with self.assertRaises(AssertionError):
            tool.capture_editor(check, 'sign_editor_shown', {})
        self.assertEqual([], check.controls['edge_control'].writes)

    def test_hiding_failure_restores_controls_before_returning_error(self):
        check = Check()
        edge = check.controls['edge_control']
        original_set = edge.SetVisible
        def failing_set(value):
            original_set(value)
            if not value:
                raise RuntimeError('hide failed')
        edge.SetVisible = failing_set
        with self.assertRaisesRegex(RuntimeError, 'hide failed'):
            tool.capture_editor(check, 'sign_editor_shown', {})
        self.assertTrue(edge.GetVisible())

    def test_actual_hud_toggle_restores_visible_and_already_hidden_states(self):
        for original in (0, 1):
            with self.subTest(original=original):
                check = Check()
                option = SimpleNamespace(value=original)
                view = SimpleNamespace(GetToggleOption=lambda unused: option.value,
                    SetToggleOption=lambda unused, value: setattr(option, 'value', int(value)) or True)
                check.namespace.update(sys=SimpleNamespace(),
                    b=SimpleNamespace(level=1, factory=SimpleNamespace(CreatePlayerView=lambda unused: view)),
                    api=SimpleNamespace(GetMinecraftEnum=lambda: SimpleNamespace(
                        OptionId=SimpleNamespace(HIDE_HUD=42))))
                self.assertEqual(1, check.run(tool.SAVE_HUD)['during'])
                self.assertEqual(original, check.run(tool.RESTORE_HUD)['restored'])
                self.assertFalse(hasattr(check.namespace['sys'], '_sign_visual_hud_saved'))

    def test_hud_setup_failure_rolls_back_the_actual_toggle(self):
        check = Check()
        option = SimpleNamespace(value=0)
        def failing_toggle(unused, value):
            option.value = int(value)
            return not value
        view = SimpleNamespace(GetToggleOption=lambda unused: option.value,
                               SetToggleOption=failing_toggle)
        check.namespace.update(sys=SimpleNamespace(),
            b=SimpleNamespace(level=1, factory=SimpleNamespace(CreatePlayerView=lambda unused: view)),
            api=SimpleNamespace(GetMinecraftEnum=lambda: SimpleNamespace(
                OptionId=SimpleNamespace(HIDE_HUD=42))))
        with self.assertRaises(AssertionError):
            check.run(tool.SAVE_HUD)
        self.assertEqual(0, option.value)
        self.assertFalse(hasattr(check.namespace['sys'], '_sign_visual_hud_saved'))


if __name__ == '__main__':
    unittest.main()
