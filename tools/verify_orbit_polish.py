"""Run input/depth recovery and atlas UI checks, preserving the current draft."""
import time
import sys
import json
import base64
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
import verify_polish53_regressions
import verify_font_share_polish
import verify_preview_recovery


def background_snapshot(name):
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    unused_x,unused_y,width,height=capture._window_rect(window['hwnd'])
    capture._capture_window_windows(window['hwnd'],width,height,False,str(ui.OUT/(name+'.png')))


def background_depth():
    from verify_selection_scope import diagnostic,wait_preview,click_point
    game('api._background_editor=(s.editor,s.name,s.page,s.direct_mode,s.section,s.solo_layer,s.focused,s.box_anchor)\n_result=True')
    try:
        diagnostic({'fixture':'interior','size':[8,8,8],'camera':[0,0,1]});wait_preview()
        ui.click('选取')
        builds=diagnostic()['previewBuilds']
        ui.click('前移');ui.click('前移');time.sleep(.5)
        ui.check('callback: depth preserves scale and cached meshes',diagnostic()['depth']==2 and diagnostic()['pose'][2]==1 and diagnostic()['previewBuilds']==builds)
        click_point((4.5,4.5,5))
        ui.check('callback: inside picking reaches enclosed gold',diagnostic()['focused']==[4,4,4])
        background_snapshot('stage54_inside_gold')
        ui.click('擦除');ui.click('单格');click_point((4.5,4.5,5));wait_preview()
        ui.check('callback: inside erase removes one block',diagnostic()['blocks']==296)
        ui.click('历史');ui.click('撤销');wait_preview();ui.click('参数')
        ui.check('callback: undo restores enclosed block',diagnostic()['blocks']==297)
    finally:
        game('s.editor,s.name,s.page,s.direct_mode,s.section,s.solo_layer,s.focused,s.box_anchor=api._background_editor\ns.reset_camera(False)\ns.refresh_preview()\ns.emit()\n_result=True')
        wait_preview()


def final_checks():
    payload=(ui.OUT/'stage54_current_document.json').read_text(encoding='utf8')
    value=game('''import json
import gui
from modern_projection.pyreact import host
from modern_projection.projection.model import Document
expected=Document.from_data(json.loads(%r))
_result={'exact_draft':s.editor.document.blocks==expected.blocks and s.editor.document.size==expected.size and s.editor.document.name==expected.name,
         'blocks':len(s.editor.document.blocks),'pending':s.preview_pending,'error':s.preview_error,
         'input_callback':gui.handle_input_mode_change.func_name,'frame_callback':host.notify_game_render_tick.func_name,
         'temporary_progress':hasattr(api,'_font_progress')}
'''%payload)
    ui.check('original maximum ellipsoid restored exactly',value['exact_draft'] and value['blocks']==20649)
    ui.check('preview settles without an active test or error',not value['pending'] and not value['error'] and not value['temporary_progress'])
    ui.check('SDK input callback and render callback restored',value['input_callback']=='handle_input_mode_change' and value['frame_callback']=='notify_game_render_tick')
    files=list((ui.ROOT/'behavior_pack/modern_projection/projection').glob('*.py'))
    for path in files:
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        game('import base64\ncompile(base64.b64decode('+repr(encoded)+'),'+repr(path.name)+',"exec")\n_result=True')
    ui.check('embedded Python 2 compiles all %d projection modules'%len(files),True)
    (ui.OUT/'stage54_final_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


def main():
    if '--final-only' in sys.argv:
        final_checks()
        return
    background='--background' in sys.argv
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and (background or capture._activate_window(window['hwnd']))
    game('''from modern_projection.pyreact import navigator
from modern_projection.projection.ui import Workspace
if not navigator.contains('modern_projection_workspace'):
    navigator.push(Workspace(session=s),key='modern_projection_workspace')
_result=True''')
    time.sleep(1.)
    if background:
        verify_preview_recovery.snapshot=background_snapshot
        verify_font_share_polish.snapshot=background_snapshot
        if '--ui-only' not in sys.argv:
            background_depth()
            verify_preview_recovery.main()
    else:
        verify_polish53_regressions.main()
    verify_font_share_polish.main(background)
    (ui.OUT/'stage54_ui_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
