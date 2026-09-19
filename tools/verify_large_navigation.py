"""Maximum-size exact model, clipping, cutaway and panned interior picking."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_large_editor import snapshot
from verify_viewport_revision import action


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    ui.click('工作台');ui.click('浏览')
    diagnostic({'fixture':'solid','size':[256,384,256]})
    state,seconds=wait_preview()
    ui.check('maximum document and native scene retain all three exact dimensions',state['size']==state['sceneSize']==[256,384,256])
    ui.check('maximum solid keeps all 25,165,824 blocks',state['blocks']==25165824)
    # Native geometry upload may outlive the Python build-complete notification.
    time.sleep(3.)
    snapshot('maximum_navigation_overview')
    diagnostic({'layer':191,'camera':[0,90,1]});ui.click('切面');wait_preview()
    time.sleep(.8);click_point((128.5,192,128.5))
    ui.check('cutaway picks Y191 inside a maximum solid',diagnostic()['focused']==[128,191,128])
    ui.check('cutaway preserves original full solid data',diagnostic()['blocks']==25165824)
    diagnostic({'camera':[0,90,20]});time.sleep(1.)
    action(glyph='arrow_right',width=27,height=27);time.sleep(.7)
    click_point((128.5,192,128.5))
    ui.check('20x zoom and panning still pick exact interior voxel',diagnostic()['focused']==[128,191,128])
    snapshot('maximum_navigation_cutaway')
    ui.click('切面');wait_preview();action(glyph='home');time.sleep(.8)
    ui.check('restoring view preserves the one full-volume selection',diagnostic()['selection']==25165824)
    (ui.OUT/'large_navigation_checks.json').write_text(json.dumps({'buildSeconds':seconds,'checks':ui.checks},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
