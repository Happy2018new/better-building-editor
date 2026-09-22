"""Foreground pixels and real PC/F11 cancel/retry clicks for preview status."""
import json
import time
import sys
import base64
import mss
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
import verify_font_share_polish
from native_input_mode import set_touch, state


def activate_bound_window(window):
    assert capture._activate_window(window['hwnd']),'Cannot activate bound game window'


def snap(name):
    name=name.replace('stage53_', 'stage55_').replace('stage54_', 'stage55_')
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground before capture'
    left,top,width,height=capture._window_rect(window['hwnd'])
    with mss.MSS() as screen:
        raw=screen.grab(dict(left=left,top=top,width=width,height=height))
        Image.frombytes('RGB',raw.size,raw.bgra,'raw','BGRX').save(ui.OUT/(name+'.png'))


def progress_button(label):
    progress=ui.nodes('PreviewProgress',ui.call('dump_tree')['tree'])[0]
    action=next(n for n in ui.nodes('PreviewAction',progress) if n['props'].get('label')==label)
    return ui.nodes('Pointer',action)[0]


def native_click(button, window, drag_out=False):
    control=ui.call('native_control',button['id'])['result']
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    left,top,width,unused=capture._window_rect(window['hwnd'])
    scale=width/root['width']
    x=int(left+(control['global'][0]+control['size'][0]/2.)*scale)
    y=int(top+(control['global'][1]+control['size'][1]/2.)*scale)
    assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground before click'
    capture.user32.SetCursorPos(x,y);time.sleep(.12)
    assert capture.user32.GetForegroundWindow()==window['hwnd'],'Game lost foreground before press'
    capture.user32.mouse_event(2,0,0,0,0)
    try:
        time.sleep(.085)
        if drag_out:
            capture.user32.SetCursorPos(x-90,y)
            time.sleep(.15)
    finally:capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.4)


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window
    if '--wait-foreground' in sys.argv:
        deadline=time.monotonic()+120.
        print('Waiting for the bound Minecraft window to receive foreground focus...',flush=True)
        while capture.user32.GetForegroundWindow()!=window['hwnd'] and time.monotonic()<deadline:
            time.sleep(.25)
        assert capture.user32.GetForegroundWindow()==window['hwnd'],'No foreground focus received within 120 seconds'
    else:
        activate_bound_window(window)
    original_mode=state()['simulated']
    game('''from HelloScript.pyreact import navigator
from HelloScript.projection.ui import Workspace
if not navigator.contains('modern_projection_workspace'):
    navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
    time.sleep(.6)
    if '--reload-ui-code' in sys.argv:
        close=next(n for n in ui.nodes('Action') if n['props'].get('glyph')=='close')
        ui.call('click',ui.nodes('Button',close)[0]['id'])
        for unused in range(30):
            if not game('from HelloScript.pyreact import navigator\n_result=navigator.contains("modern_projection_workspace")'):break
            time.sleep(.1)
        for name in ('scene','ui'):
            code=base64.b64encode((ui.ROOT/('behavior_pack/HelloScript/projection/'+name+'.py')).read_bytes()).decode('ascii')
            game('import base64\nfrom HelloScript.projection import '+name+' as module\nexec(compile(base64.b64decode('+repr(code)+'),'+repr(name+'.py')+',"exec"),module.__dict__)\n_result=True')
        game('''from HelloScript.projection.ui import Workspace
from HelloScript import HelloClientSystem
HelloClientSystem.Workspace=Workspace
navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
        time.sleep(1.)
    game('''import json
api._finish_saved=(s.page,s.preview_pending,s.preview_error,s.tiles.report_progress,s.tiles.progress)
api._finish_document=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)
s.set('page','workspace')
_result=True''')
    try:
        for touch in (() if '--font-share-only' in sys.argv else (False,True)):
            set_touch(touch)
            name='touch' if touch else 'pc'
            game('''s.preview_pending=True
s.preview_error=''
s.tiles.report_progress=True
s.tiles.progress=lambda:(24,128)
_result=True''')
            time.sleep(.4)
            pointer_before=game('_result=list(s.pointer_stats)')
            snap('stage55_progress_'+name)
            native_click(progress_button('取消'),window,drag_out=True)
            ui.check(name+' dragging off cancel does not activate it',game('_result=s.preview_pending and not s.preview_error'))
            # Re-enter, cancel, then retry without any pointer displacement.
            native_click(progress_button('取消'),window)
            ui.check(name+' real cancel ends preview work',game('_result=not s.preview_pending and not s.tiles.running and s.tiles.iterator is None and "取消" in s.preview_error'))
            ui.check(name+' cancel does not click underlying model',game('_result=list(s.pointer_stats)')==pointer_before)
            snap('stage55_cancelled_'+name)
            game('s.tiles.progress=api._finish_saved[4]\n_result=True')
            native_click(progress_button('重试'),window)
            for unused in range(150):
                result=game('_result={"pending":s.preview_pending,"error":s.preview_error}')
                if not result['pending']:break
                time.sleep(.1)
            if result['pending'] or result['error']:
                print('Retry state: '+json.dumps(dict(result,pointer=game('_result=list(s.pointer_stats)'),before=pointer_before),ensure_ascii=False),flush=True)
                snap('stage55_failed_retry_'+name)
            ui.check(name+' real retry completes preview',not result['pending'] and not result['error'])
            ui.check(name+' retry does not click underlying model',game('_result=list(s.pointer_stats)')==pointer_before)
            ui.check(name+' cancel/retry preserves every block',game('_result=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._finish_document'))
            (ui.OUT/'stage55_native_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        set_touch(original_mode)
        if '--progress-only' not in sys.argv:
            verify_font_share_polish.snapshot=snap
            verify_font_share_polish.main()
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
        game('''s.page,s.preview_pending,s.preview_error,s.tiles.report_progress,s.tiles.progress=api._finish_saved
s.emit()
_result=True''')
        set_touch(original_mode)
        ui.check('document restored exactly after foreground inspection',game('_result=json.dumps(s.editor.document.to_data(),sort_keys=True,ensure_ascii=True)==api._finish_document'))
        report=('stage55_progress_checks.json' if '--progress-only' in sys.argv else
                'stage55_font_checks.json' if '--font-share-only' in sys.argv else 'stage55_foreground_checks.json')
        (ui.OUT/report).write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')
        game('''for name in list(vars(api)):
    if name.startswith('_finish_'):
        delattr(api,name)
_result=True''')


if __name__=='__main__':main()
