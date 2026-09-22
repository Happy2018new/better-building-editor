"""Native PC/F11 scrollbar capture, without changing the user's document."""
import ast
import base64
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from native_input_mode import set_touch, state


def install():
    path=ui.ROOT/'behavior_pack/HelloScript/pyreact/primitives.py'
    source=path.read_text(encoding='utf8')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.ClassDef) and n.name=='ScrollViewPrimitive')
    patch='\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
    code=base64.b64encode(patch.encode('utf8')).decode('ascii')
    game('''import base64
from HelloScript.pyreact import primitives,native
ns=dict(primitives.__dict__)
exec(compile(base64.b64decode('''+repr(code)+'''),'<scroll-fix>','exec'),ns)
for name in ('_get_scroll_view','scroll_to_percent'):
    getattr(primitives.ScrollViewPrimitive,name).func_code=getattr(ns['ScrollViewPrimitive'],name).func_code
h=native.get_top_screen()
for slot in getattr(h,'_projection_pointer_surfaces',()):
    cb=slot.props.get('onDown')
    if not cb or not cb.func_closure: continue
    refs=dict(zip(cb.func_code.co_freevars,[c.cell_contents for c in cb.func_closure]))
    view=refs.get('view')
    if view and view.current and hasattr(view.current,'_pyreact_scroll_control'):
        del view.current._pyreact_scroll_control
_result=True''')
    source=(ui.ROOT/'behavior_pack/HelloScript/projection/widgets.py').read_text(encoding='utf8')
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='Scroll')
    patch='from __future__ import unicode_literals\n@Component\n'+'\n'.join(source.splitlines()[node.lineno-1:node.end_lineno])
    code=base64.b64encode(patch.encode('utf8')).decode('ascii')
    game('''from HelloScript.projection import widgets
import sys
ns=dict(widgets.__dict__)
exec(compile(base64.b64decode('''+repr(code)+'''),'<scroll-component>','exec'),ns)
for module_name,module in tuple(sys.modules.items()):
    if not module_name.startswith('HelloScript.projection'):continue
    component=getattr(module,'Scroll',None)
    if component is not None and hasattr(component,'_render'):
        component._render.func_code=ns['Scroll']._render.func_code
from HelloScript.pyreact import navigator
from HelloScript.projection.ui import Workspace
navigator.pop()
_result=True''')
    time.sleep(.6)
    game("navigator.push(Workspace(session=s),key='modern_projection_workspace')\n_result=True")
    time.sleep(3.)


def controls():
    scroll=ui.nodes('Scroll')[1]
    target=ui.nodes('Pointer',scroll)[0]
    view=ui.nodes('VisibleScroll',scroll)[0]
    game('''from HelloScript.pyreact import native,debug
from HelloScript.pyreact.primitives import ScrollViewPrimitive
h=native.get_top_screen()
v=debug.find_fiber_by_id(h._root_fiber,'''+repr(view['id'])+''')
vc=h.GetBaseUIControl(v.native_path)
ScrollViewPrimitive.scroll_to_top(vc)
t=debug.find_fiber_by_id(h._root_fiber,'''+repr(target['id'])+''').primitive_state['pointer_tracker']
api._rail_events=[]
def wrap_tracker(tracker):
    original=tracker.send
    def logged(name,args):
        api._rail_events.append((name,dict(args)))
        original(name,args)
    tracker.send=logged
wrap_tracker(t)
_result=True''')
    time.sleep(.15)
    print(game('_result={"viewSize":vc.GetSize(),"downNames":t.props["onDown"].func_code.co_freevars,"source":t.props["onDown"].func_code.co_filename}'),flush=True)
    return target, ui.call('native_control',target['id'])['result']


def main():
    install()
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd']), 'FOCUS_DENIED'
    initial_touch=state()['simulated']
    try:
        for touch in (False,True):
            set_touch(touch)
            time.sleep(3.)  # Allow deferred parameter rows to settle before measuring range.
            target,rail=controls()
            left,top,width,height=capture._window_rect(window['hwnd'])
            scale=width/float(game('_result=s.bridge.factory.CreateGame(s.bridge.level).GetScreenSize()[0]'))
            x=rail['global'][0]+rail['size'][0]/2
            y=rail['global'][1]+8
            def move(px,py):
                assert capture.user32.GetForegroundWindow()==window['hwnd'],'FOCUS_LOST'
                capture.user32.SetCursorPos(int(left+px*scale),int(top+py*scale))
            move(x,y);time.sleep(.15)
            capture.user32.mouse_event(2,0,0,0,0)
            try:
                time.sleep(.1)
                positions=[]
                for i in range(1,13):
                    move(x-30*i/12.,y+60*i/12.)
                    time.sleep(.035)
                    if i in (4,8,12):
                        positions.append(game('_result=ScrollViewPrimitive.get_scroll_position(vc)'))
                print({'touch':touch,'positions':positions,'native':ui.call('native_control',target['id'])},flush=True)
                print(game('_result={"events":[(n,a.get("TouchEvent"),a.get("TouchId"),a.get("TouchPosX"),a.get("TouchPosY")) for n,a in api._rail_events],"click":h._projection_last_click}'),flush=True)
                ui.check(('F11' if touch else 'PC')+' held drag keeps scrolling outside rail',
                    positions[0]>0 and positions[1]>positions[0]+10 and positions[2]>positions[1]+10)
            finally:
                capture.user32.mouse_event(4,0,0,0,0)
            time.sleep(.15)
            native=ui.call('native_control',target['id'])['result']
            ui.check('release ends capture',not native['pointerPressed'] and not native['pointerPolling'])
            before=game('_result=ScrollViewPrimitive.get_scroll_position(vc)')
            move(x-10,y+10);time.sleep(.15)
            after=game('_result=ScrollViewPrimitive.get_scroll_position(vc)')
            ui.check('released hover does not scroll',abs(before-after)<.1)
            if touch:
                ui.check('touch capture restores the original rail rectangle',
                    native['size']==rail['size'] and native['global']==rail['global'])
                move(x-10,y+20);time.sleep(.1)
                capture.user32.mouse_event(2,0,0,0,0)
                try:
                    for step in range(1,9):
                        move(x-10,y+20+step*3);time.sleep(.035)
                    scrolled=game('_result=ScrollViewPrimitive.get_scroll_position(vc)')
                    ui.check('ordinary touch content scrolling resumes after rail release',scrolled<after-10)
                finally:
                    capture.user32.mouse_event(4,0,0,0,0)
            print({'touch':touch,'positions':positions,'final':after},flush=True)
    finally:
        set_touch(initial_touch)
        (ui.OUT/'scrollbar61_checks.json').write_text(json.dumps(ui.checks,indent=2),encoding='utf8')


if __name__=='__main__':main()
