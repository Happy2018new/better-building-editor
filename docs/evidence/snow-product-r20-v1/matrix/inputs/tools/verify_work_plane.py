"""Native PC/F11 picking of raised empty grid cells above the demo's trees."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game
from verify_selection_scope import diagnostic, wait_preview
from verify_global_cursor import hover, screen_point
from verify_interaction import pointer
from verify_large_editor import snapshot
from native_input_mode import set_touch
from projection.camera import OrbitCamera, layer_hit, raycast
from projection.model import demo_document


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])

    def click(pos):
        hover(pos)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.06)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.4)
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'

    def mode(value):
        game('s.choose_mode(%r)\n_result=True'%value);time.sleep(.25)

    try:
        for touch in (False,True):
            set_touch(touch);time.sleep(.8)
            diagnostic.identity=None
            diagnostic({'fixture':'demo','layer':8,'camera':[0,90,1]});wait_preview()
            game('s.set("grid",True)\n_result=True')
            mode('select')
            click((20.5,8.,3.5))
            prefix='F11 ' if touch else 'PC '
            ui.check(prefix+'raised grid selects empty cell instead of lower leaves',diagnostic()['focused']==[20,8,3])
            mode('box');click((20.5,8.,3.5))
            ui.check(prefix+'first box corner uses the raised grid',diagnostic()['anchor']==[20,8,3])
            click((21.5,8.,4.5))
            state=diagnostic()
            ui.check(prefix+'second corner commits a flat grid rectangle',state['selection']==4 and state['start'][1]==state['end'][1]==8)
            mode('place');before=diagnostic()['blocks']
            click((20.5,8.,3.5));wait_preview()
            ui.check(prefix+'one click places directly on raised empty grid',
                     game('_result=s.editor.document.get((20,8,3)) != ("minecraft:air",0)') and diagnostic()['blocks']==before+1)
            game('s.action(s.editor.undo)\n_result=True');wait_preview()
            mode('select');game('s.set("grid",False)\n_result=True');time.sleep(.2)
            click((20.5,8.,3.5))
            ui.check(prefix+'hiding grid allows picking the lower tree',diagnostic()['focused']==[20,5,3])
            game('s.set("grid",True)\ns.layer(2)\n_result=True');time.sleep(.25)
            click((20.5,6.,3.5))
            ui.check(prefix+'tree in front of the lower grid retains priority',diagnostic()['focused']==[20,5,3])
        set_touch(False);diagnostic.identity=None
        diagnostic({'fixture':'demo','layer':8,'camera':[35,25,1.7]});wait_preview();mode('select')
        state=diagnostic();box=pointer()['layout']
        camera=OrbitCamera(*state['pose']);camera.pan=tuple(state['pan']);camera.pivot=state.get('cameraPivot')
        xy=screen_point((20.5,6.,3.5))
        ray=camera.ray(*xy,state['sceneSize'],box['width'],box['height'],
                       min(box['width'],box['height'])*.72*state['pose'][2]/max(state['sceneSize']))
        expected=layer_hit(demo_document(),*ray,8)
        ui.check('angled fixture points through grid to an actual lower block',expected is not None and raycast(demo_document(),*ray)[0][1]<8)
        hover((20.5,6.,3.5))
        ui.check('angled hover previews the raised grid cell',diagnostic()['cursorCell']==list(expected))
        click((20.5,6.,3.5))
        ui.check('angled click and hover select the same grid cell',diagnostic()['focused']==list(expected))
        snapshot('work_plane_above_tree')
    finally:
        set_touch(False)
        (ui.OUT/'work_plane_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
