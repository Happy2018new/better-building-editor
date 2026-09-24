"""Esc with native input focus, projection layouts and touch release pixels."""
import json
import subprocess
import sys
import time
from PIL import ImageGrab
import verify_ui as ui
import capture_screen as capture
from verify_projection_outline import game
from verify_large_editor import snapshot
from native_input_mode import key, state, set_touch, open_workspace


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_touch=state()['simulated']
    original_page=game('_result=s.page')
    original_size=capture._window_rect(window['hwnd'])[2:]

    def exists():
        return game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")')

    def reopen():
        if not exists():open_workspace();time.sleep(2.)

    def native(node):
        if node['type'] not in ('Input','Button'):node=ui.nodes('Button',node)[0]
        return ui.call('native_control',node['id'])['result']

    def point(node, fraction=(.5,.5)):
        ctrl=native(node)
        left,top,width,height=capture._window_rect(window['hwnd'])
        scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        return tuple(int(a+(b+d*k)*scale) for a,b,d,k in zip((left,top),ctrl['global'],ctrl['size'],fraction))

    def click(node):
        pos=point(node)
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        capture.user32.SetCursorPos(*pos);time.sleep(.15)
        capture.user32.mouse_event(2,0,0,0,0)
        try:time.sleep(.07)
        finally:capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.55)
        actual=capture.POINT();capture.user32.GetCursorPos(capture.ctypes.byref(actual))
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground'
        assert abs(actual.x-pos[0])<3 and abs(actual.y-pos[1])<3,'Pointer moved during test'

    def action(label):
        return next(n for n in ui.nodes('Action') if n['props'].get('label')==label)

    def pixel(node):
        # Sample a flat surface away from the icon, text, rounded corners and pointer.
        x,y=point(node,(.5,.15))
        return ImageGrab.grab(bbox=(x,y,x+1,y+1)).getpixel((0,0))

    try:
        reopen();set_touch(False)
        game('s.set("pending_rename",(999,"Esc test"))\n_result=True');time.sleep(.6)
        field=ui.nodes('Input',ui.nodes('RenameDialog')[0])[0]
        click(field)
        ui.check('rename input has real native focus',native(field)['displayText']['properties'].get('#text_edit_selected'))
        key('esc');time.sleep(.5)
        ui.check('Esc dismisses focused rename without leaving workspace',exists() and game('_result=s.pending_rename is None'))
        game('s.open_materials("material")\n_result=True');time.sleep(1.)
        field=ui.nodes('Input',ui.nodes('MaterialBrowser')[0])[0]
        click(field)
        ui.check('catalogue search has real native focus',native(field)['displayText']['properties'].get('#text_edit_selected'))
        key('esc');time.sleep(.5)
        ui.check('Esc dismisses focused catalogue without leaving workspace',exists() and game('_result=s.material_browser is None'))
        game('s.set("page","projection")\n_result=True');time.sleep(1.)
        for preset in ('4:3','16:9'):
            subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                            '--preset',preset],check=True,capture_output=True)
            time.sleep(.6)
            settings=ui.nodes('ProjectionSettings')[0]
            scroll=ui.nodes('ScrollView',settings)[0]
            ui.call('scroll',scroll['id'],10000);time.sleep(.3)
            speed=next(n for n in ui.nodes('Range',settings) if n['props'].get('label')=='炫彩流动速度')
            slider=ui.call('native_control',ui.nodes('Slider',speed)[0]['id'])['result']
            area=ui.call('native_control',scroll['id'])['result']
            ui.check(preset+' outline speed is fully reachable by scrolling',area['global'][1]<=slider['global'][1] and slider['global'][1]+slider['size'][1]<=area['global'][1]+area['size'][1]+1)
            snapshot('stage49_projection_speed_'+preset.replace(':','_'))
            ui.call('scroll',scroll['id'],0)
        field=ui.nodes('Input',ui.nodes('ProjectionSettings')[0])[0]
        click(field)
        key('esc');time.sleep(.5)
        ui.check('Esc closes workspace while an ordinary coordinate input is focused',not exists())
        reopen()
        game('s.set("page","workspace")\n_result=True');time.sleep(.6)
        set_touch(True);time.sleep(.5)
        target=action('左移')
        capture.user32.SetCursorPos(*point(action('右移')));time.sleep(.3)
        base=pixel(target)
        click(target)
        released=pixel(action('左移'))
        untouched=pixel(action('右移'))
        ui.check('released touch button pixels return to base and match neighboring button',max(abs(a-b) for a,b in zip(base,released))<=2 and max(abs(a-b) for a,b in zip(untouched,released))<=2)
        snapshot('stage49_touch_button_pixels')
    finally:
        (ui.OUT/'stage49_controls_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        game('s.set("pending_rename",None)\ns.set("material_browser",None)\ns.set("page",'+repr(original_page)+')\n_result=True')
        reopen();set_touch(original_touch)
        subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                        '--size','%dx%d'%tuple(original_size)],check=True,capture_output=True)


if __name__=='__main__':main()
