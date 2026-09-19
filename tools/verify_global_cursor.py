"""Real hover in each mode and touch-safe destructive actions."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import pointer
from projection.camera import OrbitCamera
from verify_large_editor import snapshot


def screen_point(pos):
    state=diagnostic();box=pointer()['layout']
    cam=OrbitCamera(*state['pose']);cam.pan=tuple(state['pan'])
    local=tuple(pos[i]-state['origin'][i] for i in range(3))
    return cam.project(local,state['sceneSize'],box['width'],box['height'],
                       min(box['width'],box['height'])*.72*state['pose'][2]/max(state['sceneSize']))


def hover(pos):
    x,y=screen_point(pos);box=pointer()['layout']
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
    capture.user32.SetCursorPos(int(left+(box['x']+x)*scale),int(top+(box['y']+y)*scale));time.sleep(.3)


def touch(pos, drag=False):
    x,y=screen_point(pos);node=pointer()['id']
    ui.call('pointer',node,{'phase':'down','x':x,'y':y,'touch':True})
    if drag:
        ui.call('pointer',node,{'phase':'move','x':x+20,'y':y,'touch':True})
        x+=20
    ui.call('pointer',node,{'phase':'leave','x':x,'y':y,'touch':True})
    ui.call('pointer',node,{'phase':'up','x':x,'y':y,'touch':True});time.sleep(.3)


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台');diagnostic({'fixture':'solid','camera':[0,90,1]});wait_preview()
    for mode in ('浏览','选取','换材质','擦除','吸管','框选'):
        ui.click(mode)
        if mode=='擦除':ui.click('单格')
        before=diagnostic()
        hover((6.5,16,8.5));a=diagnostic()
        hover((10.5,16,8.5));b=diagnostic()
        ui.check(mode+' hover follows the actual voxel',a['cursorCell']==[6,15,8] and b['cursorCell']==[10,15,8])
        ui.check(mode+' hover never mutates the formal selection or blocks',
                 all(before[k]==b[k] for k in ('start','end','selection','blocks')))
    snapshot('global_hover_box_mode')
    ui.click('擦除');ui.click('单格');before=diagnostic()['blocks']
    touch((6.5,16,8.5));after=diagnostic()
    ui.check('touch erase retains a candidate without deleting on release',after['touch'] and
             after['placementTarget']==[6,15,8] and after['blocks']==before)
    ui.click('确认擦除');wait_preview()
    ui.check('touch erase confirmation deletes exactly once',diagnostic()['blocks']==before-1)
    touch((10.5,16,8.5));ui.click('取消')
    ui.check('cancel clears touch candidate without further edits',diagnostic()['placementTarget'] is None and diagnostic()['blocks']==before-1)
    touch((10.5,16,8.5),True)
    ui.check('touch orbit does not erase or create a candidate',diagnostic()['placementTarget'] is None and diagnostic()['blocks']==before-1)
    ui.click('换材质');diagnostic({'camera':[0,90,1]});time.sleep(.7)
    touch((10.5,16,8.5))
    ui.check('touch paint previews the touched cell and exposes confirmation',diagnostic()['placementTarget']==[10,15,8] and '确认换材质' in ui.labels())
    ui.click('选取')
    ui.check('mode switching cancels the destructive touch proposal',diagnostic()['placementTarget'] is None)
    touch((8.5,16,8.5))
    ui.check('touch selection immediately retains its selected voxel',diagnostic()['focused']==[8,15,8])
    ui.click('放置');ui.click('触控放置')
    (ui.OUT/'global_cursor_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
