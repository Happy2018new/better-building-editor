"""Background native mounts must not interrupt focused input or gestures."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


class PreparationTests(unittest.TestCase):
    def setUp(self):
        api=types.ModuleType('mod.client.extraClientApi')
        modules={name:types.ModuleType(name) for name in ('prep_test','prep_test.projection','prep_test.pyreact',
                                                       'prep_test.pyreact.hooks','mod','mod.client')}
        modules['mod.client.extraClientApi']=api
        ui=modules['prep_test.pyreact']
        ui.Component=lambda f:f
        for name in ('Panel','use_state','use_effect','use_ref','use_event'):
            setattr(ui,name,lambda *a,**k:None)
        modules['prep_test.pyreact.hooks'].use_animation_frame=lambda *a:None
        self.scope=patch.dict(sys.modules,modules)
        self.scope.start();self.addCleanup(self.scope.stop)
        path=Path(__file__).resolve().parents[1]/'behavior_pack/HelloScript/projection/preparation.py'
        spec=importlib.util.spec_from_file_location('prep_test.projection.preparation',path)
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        self.focus=False
        control=types.SimpleNamespace(GetPropertyBag=lambda:{'#text_edit_selected':self.focus})
        self.host=types.SimpleNamespace(_input_handlers={'search':None},GetBaseUIControl=lambda path:control)
        api.GetTopScreen=lambda:self.host
        self.session=types.SimpleNamespace(camera_dragging=False,edit_job=None,busy=False,
                                          material_browser=None,pending_rename=None,pending_confirm=None)
        self.queue=module.PreparationQueue(self.session)
        self.queue.ready=True
        self.calls=[]

    def test_typing_pauses_native_mounts_until_focus_is_released(self):
        self.queue.add(lambda:self.calls.append('mounted'))
        self.focus=True;self.queue.step(100)
        self.assertEqual([],self.calls)
        self.focus=False;self.queue.step(101)
        self.assertEqual(['mounted'],self.calls)

    def test_holds_and_camera_drags_pause_preparation(self):
        self.queue.add(lambda:self.calls.append('mounted'))
        self.host._projection_click_contacts={0};self.queue.step(100)
        self.host._projection_click_contacts=set();self.session.camera_dragging=True;self.queue.step(101)
        self.assertEqual([],self.calls)
        self.session.camera_dragging=False;self.queue.step(102)
        self.assertEqual(['mounted'],self.calls)

    def test_visible_pane_wins_but_only_one_batch_runs_per_frame(self):
        self.queue.add(lambda:self.calls.append('background'))
        self.queue.add(lambda:self.calls.append('visible'),lambda:True)
        self.queue.step(100);self.assertEqual(['visible'],self.calls)
        self.queue.step(101);self.assertEqual(['visible','background'],self.calls)

    def test_cancelled_or_closed_workspace_never_mounts_queued_controls(self):
        cancel=self.queue.add(lambda:self.calls.append('cancelled'));cancel()
        self.queue.add(lambda:self.calls.append('live'))
        self.queue.ready=False;self.queue.step(100);self.assertEqual([],self.calls)
        self.queue.ready=True;self.queue.step(101);self.assertEqual(['live'],self.calls)

    def test_rebound_and_page_animations_complete_before_background_mounts(self):
        for name in ('Action','JellyButton','PageMotion','Animated'):
            fiber=types.SimpleNamespace(_mounted=True,comp_type=types.SimpleNamespace(__name__=name))
            slot={'active':True,'fiber':fiber}
            self.host._animation_frames={1:slot}
            self.queue.add(lambda:self.calls.append('mounted'))
            self.queue.step(100);self.assertEqual([],self.calls)
            slot['active']=False;self.queue.step(101)
            self.assertEqual(['mounted'],self.calls);self.calls.clear()
            self.queue.next_batch_at=0.

    def test_background_work_leaves_time_between_batches(self):
        self.queue.add(lambda:self.calls.append('first'))
        self.queue.add(lambda:self.calls.append('second'))
        self.queue.step(100);self.queue.step(100.01)
        self.assertEqual(['first'],self.calls)
        self.queue.step(100.04);self.assertEqual(['first','second'],self.calls)


if __name__=='__main__':unittest.main()
