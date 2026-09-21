"""Measure real button squash/rebound on mouse and F11 native touch."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from native_input_mode import set_touch


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    records=[]
    original=game('_result=s.reduced_motion')
    def run(kind):
        if kind=='Action':
            target=next(n for n in ui.nodes('Action',ui.nodes('CategoryRail')[0]) if n['props'].get('glyph')=='brush')
        else:
            segment=next(n for n in ui.nodes('Segments',ui.nodes('PageNavigation')[0]))
            target=next(n for n in ui.nodes('JellyButton',segment) if n.get('key')=='workspace')
        button=ui.nodes('Button',target)[0]
        native=ui.call('native_control',button['id'])['result']
        game('''from HelloScript.pyreact.debug import find_fiber_by_id
h=api.GetTopScreen()
f=find_fiber_by_id(h._root_fiber,%r)
control=h.GetBaseUIControl(f.native_path)
h._press_samples=[]
def sample(now):
    h._press_samples.append(control.GetSize())
h._press_probe={'fiber':f,'active':True,'callback':sample}
h.pyreact_register_animation_frame(h._press_probe)
_result=True
'''%button['id'])
        try:
            left,top,width,height=capture._window_rect(window['hwnd'])
            scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
            point=tuple(int(origin+(p+size/2)*scale) for origin,p,size in zip((left,top),native['global'],native['size']))
            assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
            capture.user32.SetCursorPos(*point);time.sleep(.08)
            capture.user32.mouse_event(2,0,0,0,0)
            try:time.sleep(.065)
            finally:capture.user32.mouse_event(4,0,0,0,0)
            time.sleep(.6)
            actual=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(actual))
            assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
            assert abs(actual.x-point[0])<3 and abs(actual.y-point[1])<3,'Pointer moved during test'
            sizes=game('_result=h._press_samples[:]')
            return native['size'],sizes
        finally:
            game('h.pyreact_unregister_animation_frame(h._press_probe)\n_result=True')
    try:
        game('s.set("reduced_motion",False)\ns.set("page","workspace")\n_result=True');time.sleep(.5)
        for touch in (False,True):
            set_touch(touch);time.sleep(1.)
            for kind in ('Action','JellyButton'):
                base,sizes=run(kind)
                label=('F11 ' if touch else 'PC ')+kind
                records.append(dict(label=label,base=base,sizes=sizes))
                ui.check(label+' visibly squashes and stretches',max(v[0]/base[0] for v in sizes)>1.05 and min(v[1]/base[1] for v in sizes)<.92)
                ui.check(label+' returns exactly to its original size',all(abs(sizes[-1][i]-base[i])<.01 for i in (0,1)))
        game('s.set("reduced_motion",True)\n_result=True');time.sleep(.5)
        base,sizes=run('Action')
        ui.check('reduced motion disables the wobble',all(abs(sizes[-1][i]-v[i])<.01 for i in (0,1) for v in sizes))
    finally:
        game('s.set("reduced_motion",%r)\n_result=True'%original)
        set_touch(False)
        (ui.OUT/'press_feedback_checks.json').write_text(json.dumps(dict(checks=ui.checks,records=records),indent=2),encoding='utf8')


if __name__=='__main__':main()
