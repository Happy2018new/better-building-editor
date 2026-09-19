"""Integer new-region controls and real scrollbar capture outside the rail."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import category
from verify_large_editor import snapshot


def dimension(axis):
    return next(n for n in ui.nodes('DimensionAxis') if n['props']['axis']==axis)


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('建筑库')
    ui.check('new dimensions have no native text fields',not ui.nodes('Input',ui.nodes('NewRegion')[0]))
    ui.check('temporary maximum-size button removed','新建最大区域' not in ui.labels())
    for size in ((1,1,1),(64,100,64),(17,32,9)):
        ui.new_region(size);wait_preview()
        state=diagnostic()
        ui.check('integer controls create exact %s region'%(size,),state['size']==list(size) and state['blocks']==0)
        ui.check('selection covers the exact new region',state['selection']==size[0]*size[1]*size[2])
    ui.click('建筑库')
    for axis in range(3):
        node=dimension(axis)
        action=next(n for n in ui.nodes('Action',node) if n['props'].get('glyph')=='plus')
        ui.call('click',ui.nodes('Button',action)[0]['id']);time.sleep(.15)
    ui.click('新建空白');ui.click('确认继续');wait_preview()
    ui.check('all three plus buttons adjust exactly one block',diagnostic()['size']==[18,33,10])
    ui.click('建筑库')
    for axis in range(3):
        node=dimension(axis)
        action=next(n for n in ui.nodes('Action',node) if n['props'].get('glyph')=='minus')
        ui.call('click',ui.nodes('Button',action)[0]['id']);time.sleep(.15)
    ui.click('新建空白');ui.click('确认继续');wait_preview()
    ui.check('all three minus buttons adjust exactly one block',diagnostic()['size']==[17,32,9])
    ui.click('建筑库')
    for preset in ('20:9','4:3','16:10','16:9'):
        result=subprocess.run([sys.executable,str(ui.ROOT/'.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                               '--preset',preset],capture_output=True,encoding='utf8',check=True)
        info=json.loads(result.stdout);assert info['ok'] and info['actualClient']==info['requestedClient']
        time.sleep(.5)
        region=ui.nodes('NewRegion')[0];box=ui.nodes('Panel',region)[0]['layout']
        axes=ui.nodes('DimensionAxis',region)
        ui.check('dimension controls fit at '+preset,len(axes)==3 and all(
            n['layout']['x']>=box['x'] and n['layout']['x']+n['layout']['width']<=box['x']+box['width']+.1
            for n in ui.nodes('Button',region)+ui.nodes('Slider',region)))
    snapshot('new_region_integer_controls')
    ui.click('工作台');ui.click('浏览');category('cube');ui.click('空心长方体')
    scroll=ui.nodes('Scroll')[-1]
    view=ui.nodes('ScrollView',scroll)[0]['id'];rail=ui.nodes('Pointer',scroll)[0]['id']
    ui.call('scroll',view,0);time.sleep(.3)
    native=ui.call('native_control',rail)['result'];assert native['visible']
    x,y=native['global'];x+=native['size'][0]/2.;y+=8
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
    def move(px,py):
        assert capture.user32.GetForegroundWindow()==window['hwnd']
        capture.user32.SetCursorPos(int(left+px*scale),int(top+py*scale));time.sleep(.15)
    move(x,y)
    capture.user32.mouse_event(2,0,0,0,0)
    try:
        time.sleep(.12);move(x-80,y+35)
        first=ui.call('get_scroll',view)['result']['position']
        state=ui.call('native_control',rail)['result']
        ui.check('drag remains captured 80 UI pixels outside scrollbar',state['pointerPressed'] and state['pointerPolling'] and first>0)
        move(x-110,y+80)
        second=ui.call('get_scroll',view)['result']['position']
        ui.check('content continues following outside-rail movement',second>first+5)
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.2)
    state=ui.call('native_control',rail)['result']
    ui.check('release outside scrollbar stops capture',not state['pointerPressed'] and not state['pointerPolling'])
    position=ui.call('get_scroll',view)['result']['position'];move(x-130,y+120)
    ui.check('moving after release no longer scrolls',abs(ui.call('get_scroll',view)['result']['position']-position)<.01)
    (ui.OUT/'dimensions_capture_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
