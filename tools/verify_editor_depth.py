"""Real native selection hover, animated reset and editing inside a closed shell."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer
from verify_large_editor import snapshot
from projection.camera import OrbitCamera


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and window['process'] == 'Minecraft.Windows.exe'
    assert capture._activate_window(window['hwnd'])
    left, top, physical_width, unused = capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left+30, top+40)
    ui.click('工作台'); ui.click('完整')
    diagnostic({'fixture':'interior','size':[8,8,8],'camera':[0,0,1]}); wait_preview()
    ui.click('框选')
    box = pointer()['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    scale = physical_width/root['width']
    camera = OrbitCamera(0,0)

    def move(point, click=False):
        x,y = camera.project(point,(8,8,8),box['width'],box['height'],min(box['width'],box['height'])*.72/8.)
        capture.user32.SetCursorPos(int(left+(box['x']+x)*scale),int(top+(box['y']+y)*scale))
        time.sleep(.08)
        if click:
            capture.user32.mouse_event(2,0,0,0,0); time.sleep(.055)
            capture.user32.mouse_event(4,0,0,0,0); time.sleep(.2)

    move((2.5,2.5,8),True); move((5.5,5.5,8),True)
    state = diagnostic()
    ui.check('two real clicks finish one shared region',state['selection']==16 and state['anchor'] is None)
    capture.user32.SetCursorPos(left+30,top+40); time.sleep(.15)
    raw = ui.call('dump_tree')['tree']
    edges = [n for n in ui.nodes('Image',ui.nodes('Scene',raw)[0]) if 'rotatePivot' in n.get('props',{})][-12:]
    def outline():
        return [ui.call('native_control',n['id'])['result'] for n in edges]
    before = outline()
    move((3.5,3.5,8)); after = outline()
    ui.check('hover retains all completed box edges',all(a['visible']==b['visible'] and a['rect']==b['rect'] for a,b in zip(before,after)))
    ui.check('hover still tracks a voxel without replacing the region',diagnostic()['cursorCell']==[3,3,7] and diagnostic()['selection']==16)
    move((1.5,1.5,8),True)
    ui.check('next first corner immediately replaces the old selection',diagnostic()['selection']==1 and diagnostic()['anchor']==[1,1,7])
    move((3.5,3.5,8),True)
    ui.check('next second corner finishes the new region',diagnostic()['selection']==9 and diagnostic()['anchor'] is None)
    capture.user32.SetCursorPos(left+30,top+40)
    ui.click('选取')
    builds = diagnostic()['previewBuilds']
    ui.click('前移'); ui.click('前移'); time.sleep(.5)
    ui.check('forward crosses the shell without changing scale or building meshes',diagnostic()['depth']==2 and diagnostic()['pose'][2]==1 and diagnostic()['previewBuilds']==builds)
    click_point((4.5,4.5,5))
    ui.check('inside ray selects the enclosed gold block',diagnostic()['focused']==[4,4,4])
    snapshot('interior_gold_verified_32')
    ui.click('擦除'); ui.click('单格'); click_point((4.5,4.5,5));wait_preview()
    ui.check('enclosed block can be erased',diagnostic()['blocks']==296)
    ui.click('历史'); ui.click('撤销'); wait_preview(); ui.click('参数')
    ui.check('undo restores the enclosed block',diagnostic()['blocks']==297)
    diagnostic({'camera':[145,-20,3],'pan':[.35,-.4]});time.sleep(1)
    button = next(n for n in ui.nodes('Action') if n['props'].get('glyph')=='home')
    start = diagnostic()
    ui.call('click',ui.nodes('Button',button)[0]['id'])
    intermediate = diagnostic()
    ui.check('reset has a real intermediate animated pose',intermediate['pose']!=start['pose'] and intermediate['pose']!=[35.,25.,1.])
    time.sleep(1.4);end=diagnostic()
    ui.check('reset clears every camera dimension',end['pose']==[35.,25.,1.] and end['depth']==0 and end['pan']==[0.,0.] and end['cameraPivot'] is None)
    ui.click('建筑库');ui.click('工作台');time.sleep(.4)
    ui.check('reset survives leaving and returning to the editor',diagnostic()['pose']==[35.,25.,1.] and diagnostic()['depth']==0)
    (ui.OUT/'editor_depth_checks_32.json').write_text(json.dumps({'checks':ui.checks,'resetIntermediate':intermediate},ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    main()
