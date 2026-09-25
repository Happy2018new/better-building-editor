"""Native layer controls and injected multi-contact callbacks (not phone hardware)."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_selection_scope import diagnostic, wait_preview
from verify_large_editor import snapshot
from native_input_mode import set_touch, state


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original = state()['simulated']
    set_touch(False)
    game('s.set("page","workspace")\ns.choose_tool("fill")\ns.choose_group("edit")\n_result=True')
    diagnostic({'fixture':'demo','camera':[35,25,1]});wait_preview()
    ui.check('duplicate footer layer controls removed', '工作层 Y' not in ui.labels())
    for mode,label in [('full','网格 Y'),('section','切面 Y'),('single','单层 Y')]:
        game('s.display_mode(%r)\n_result=True'%mode);time.sleep(.25)
        view=ui.nodes('Viewport')[0]
        ui.check(mode+' has one clearly labeled layer input',label in ui.labels(view) and len(ui.nodes('Input',view))==1)
        inp=ui.nodes('Input',view)[0]
        ui.call('set_input',inp['id'],'7');time.sleep(.25)
        ui.check(mode+' layer input updates shared editing layer',diagnostic()['layer']==7)
    game('s.display_mode("full")\n_result=True');time.sleep(.3)
    snapshot('stage46_layer_controls')
    original_size=capture._window_rect(window['hwnd'])[2:]
    try:
        for preset in ('4:3','16:9'):
            subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                            '--preset',preset],check=True,capture_output=True)
            time.sleep(.65)
            view=ui.nodes('Viewport')[0]
            inp=ui.nodes('Input',view)[0]['layout']
            label=next(n for n in ui.nodes('Label',view) if n['props'].get('content')=='网格 Y')['layout']
            box=view['children'][0]['layout']
            ui.check(preset+' layer controls fit after resizing',
                     box['x']<=label['x']<inp['x'] and inp['x']+inp['width']<box['x']+box['width'])
            snapshot('stage46_layer_'+preset.replace(':','_'))
    finally:
        subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                        '--size','%dx%d'%original_size],check=True,capture_output=True)
        time.sleep(.5)
    try:
        set_touch(True)
        diagnostic({'fixture':'offset','camera':[35,25,1]});wait_preview()
        for mode in ('place','erase','box','select'):
            game('s.choose_mode(%r)\n_result=True'%mode);time.sleep(.3)
            before=diagnostic()
            game('''h=api.GetTopScreen()
t=next(t for t in h._projection_pointer_surfaces if t.props.get('onPinch'))
c=h.GetBaseUIControl(t.slot['fiber'].native_path)
x,y=c.GetGlobalPosition();w,hgt=c.GetSize()
cx,cy=x+w*.5,y+hgt*.4
span=min(w*.12,hgt*.15)
t.down({'TouchId':101,'TouchPosX':cx-span,'TouchPosY':cy,'pointerKind':'touch'})
t.down({'TouchId':102,'TouchPosX':cx+span,'TouchPosY':cy,'pointerKind':'touch'})
h._pinch_samples=[]
def sample(now):
    i=len(h._pinch_samples)
    if i>=30:
        h.pyreact_unregister_animation_frame(h._pinch_sample_slot)
        return
    k=1.+(i+1)/30.
    t.move({'TouchId':101,'TouchPosX':cx-span*k,'TouchPosY':cy})
    t.move({'TouchId':102,'TouchPosX':cx+span*k,'TouchPosY':cy})
    h._pinch_samples.append((s.zoom,s.camera_dragging,len(s.editor.document.blocks)))
h._pinch_sample_slot={'fiber':t.slot['fiber'],'active':True,'callback':sample}
h.pyreact_register_animation_frame(h._pinch_sample_slot)
_result=True''')
            time.sleep(1.4)
            samples=game('_result=h._pinch_samples')
            ui.check(mode+' pinch follows both held contacts continuously',len(samples)==30 and all(v[1] for v in samples) and
                     all(a[0]<b[0] for a,b in zip(samples,samples[1:])))
            held=diagnostic()
            ui.check(mode+' pinch doubles scale without mesh builds or editing',
                     abs(held['pose'][2]/before['pose'][2]-2.)<.001 and held['previewBuilds']==before['previewBuilds'] and
                     held['blocks']==before['blocks'] and held['selection']==before['selection'])
            game('''from HelloScript.projection.pointer import release_pointers
release_pointers(h,{'TouchId':101})
t.up({'TouchId':101})
t.move({'TouchId':102,'TouchPosX':cx+span*2.5,'TouchPosY':cy+3.})
t.move_out({'TouchId':102,'TouchEvent':6})
t.up({'TouchId':102,'TouchEvent':0})
_result=not t.pressed''')
            time.sleep(.35)
            after=diagnostic()
            ui.check(mode+' staggered releases never become taps',after['blocks']==before['blocks'] and after['anchor']==before['anchor'] and
                     after['pointerStats'][3]==before['pointerStats'][3] and not game('_result=s.camera_dragging'))
        snapshot('stage46_pinch_callbacks')
    finally:
        game('''h=api.GetTopScreen()
if hasattr(h,'_pinch_sample_slot'):h.pyreact_unregister_animation_frame(h._pinch_sample_slot)
for t in tuple(getattr(h,'_projection_pointers',())):t.cancel({})
_result=True''')
        set_touch(original)
        (ui.OUT/'layer_pinch_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
