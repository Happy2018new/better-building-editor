"""Actual placement hover/click, region erase and camera-space depth checks."""
import json
import time
import math
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer
from verify_viewport_revision import outline_edges, action
from verify_large_editor import snapshot
from projection.camera import OrbitCamera


def move_to(pos):
    state=diagnostic(); box=pointer()['layout']
    cam=OrbitCamera(*state['pose']); cam.pan=tuple(state['pan'])
    p=tuple(pos[i]-state['origin'][i] for i in range(3))
    x,y=cam.project(p,state['sceneSize'],box['width'],box['height'],
                    min(box['width'],box['height'])*.72*state['pose'][2]/max(state['sceneSize']))
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd'])
    scale=width/ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
    capture.user32.SetCursorPos(int(left+(box['x']+x)*scale),int(top+(box['y']+y)*scale))
    time.sleep(.4)


def outline_at(pos):
    time.sleep(1.)
    edges=outline_edges(); ui.check('one set of twelve cursor edges',len(edges)==12)
    centers=[]
    for edge in edges:
        native=ui.call('native_control',edge['id'])['result']
        assert native['visible'],native
        centers.append(tuple(sum(p[i] for p in native['rect'])/4. for i in (0,1)))
    center=tuple(sum(c[i] for c in centers)/12. for i in (0,1))
    state=diagnostic();box=pointer()['layout'];cam=OrbitCamera(*state['pose']);cam.pan=tuple(state['pan'])
    point=cam.project(tuple(v+.5 for v in pos),state['sceneSize'],box['width'],box['height'],
                      min(box['width'],box['height'])*.72*state['pose'][2]/max(state['sceneSize']))
    error=math.hypot(center[0]-box['x']-point[0],center[1]-box['y']-point[1])
    print('outline error',error,'native',center,'expected',point,'viewport',box,flush=True)
    ui.check('cursor marks destination '+str(pos),error<.1)


def main():
    capture.user32.SetProcessDPIAware()
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert window and window['process']=='Minecraft.Windows.exe'
    assert capture._activate_window(window['hwnd'])
    time.sleep(.5)
    ui.click('工作台')
    diagnostic({'fixture':'offset_odd','camera':[35,25,3],'pan':[.15,-.1],
                'selection':[[2,1,3],[5,3,8]]});wait_preview();ui.click('放置')
    move_to((3.5,4,5.5));outline_at((3,4,5))
    ui.check('hover preserves the existing region and block data',diagnostic()['selection']==72 and diagnostic()['blocks']==72)
    snapshot('placement_preview_before')
    capture.user32.mouse_event(2,0,0,0,0)
    try: outline_at((3,4,5))  # A press without a drag must keep the destination preview.
    finally:capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.5);wait_preview();state=diagnostic()
    ui.check('native click places and selects previewed destination',state['blocks']==73 and state['start']==state['end']==[3,4,5])
    outline_at((3,4,5));snapshot('placement_preview_after')
    move_to((4.5,4,6.5));outline_at((4,4,6))
    ui.check('moving to next target does not place another block',diagnostic()['blocks']==73)

    diagnostic({'fixture':'solid','size':[8,8,8],'camera':[35,25,1],'pan':[0,0]});wait_preview()
    move_to((4.5,8,4.5));outline_at((4,8,4))
    capture.user32.mouse_event(2,0,0,0,0)
    try:time.sleep(.08)
    finally:capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.5)
    ui.check('invalid placement preserves the region and building',diagnostic()['blocks']==512 and diagnostic()['selection']==512)
    outline_at((4,8,4));snapshot('placement_invalid_cursor')

    diagnostic({'fixture':'offset_odd','camera':[0,90,1]});wait_preview();ui.click('框选')
    click_point((3.5,4,5.5));click_point((4.5,4,6.5));ui.click('擦除')
    ui.check('framing selects region erase automatically',diagnostic()['eraseScope']=='selection' and diagnostic()['selection']==4)
    click_point((5.5,4,8.5))
    ui.check('viewport click preserves erase region',diagnostic()['selection']==4 and diagnostic()['blocks']==72)
    ui.click('擦除选区');wait_preview()
    ui.check('one action erases the four selected blocks',diagnostic()['blocks']==68 and diagnostic()['selection']==4)
    snapshot('erase_selection_result')
    ui.click('历史');ui.click('撤销');ui.click('参数');wait_preview()
    ui.check('one undo restores the whole erased region',diagnostic()['blocks']==72)
    ui.click('单格');click_point((5.5,4,8.5));wait_preview()
    ui.check('single erase remains available',diagnostic()['blocks']==71 and diagnostic()['selection']==1)

    diagnostic({'fixture':'solid','size':[8,8,8],'camera':[0,0,1],'pan':[0,0]});wait_preview();ui.click('浏览')
    zoom=diagnostic()['pose'][2]
    for label,expected in [('左移',[.12,0]),('右移',[0,0]),('上移',[0,.12]),('下移',[0,0])]:
        ui.click(label);time.sleep(.4);ui.check(label+' moves the viewpoint',diagnostic()['pan']==expected)
    click_point((3.5,3.5,8));ui.check('front face initially picked',diagnostic()['focused']==[3,3,7])
    ui.click('前移');wait_preview();click_point((3.5,3.5,7))
    ui.check('forward enters structure and picks the newly exposed layer',diagnostic()['focused']==[3,3,6])
    ui.check('depth changes preserve document and zoom',diagnostic()['blocks']==512 and diagnostic()['pose'][2]==zoom)
    snapshot('view_depth_inside')
    ui.click('后移');wait_preview();click_point((3.5,3.5,8))
    ui.check('backward restores the front wall',diagnostic()['focused']==[3,3,7] and diagnostic()['depth']==0)
    ui.click('前移');wait_preview();diagnostic({'camera':[90,0,1]});time.sleep(.9);wait_preview()
    click_point((7,3.5,3.5));ui.check('depth follows settled viewing direction',diagnostic()['focused']==[6,3,3])
    action(glyph='home');wait_preview()
    ui.check('home restores all depths and view offsets',diagnostic()['depth']==0 and diagnostic()['pan']==[0,0])
    ui.check('all six navigation buttons and section have icons and text',all(
        n['props'].get('label') and n['props'].get('glyph') for n in ui.nodes('Action',ui.nodes('ViewNavigation')[0])))
    (ui.OUT/'edit_navigation_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
