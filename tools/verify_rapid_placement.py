"""Forty real mouse clicks on a tall empty draft; no library/world writes."""
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_interaction import pointer


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('建筑库')
    field = next(n for n in ui.nodes('Coordinates') if n['props']['label'].startswith('新建尺寸'))
    ui.call('set_input', ui.nodes('Input',field)[0]['id'], '25,64,25')
    time.sleep(.3); ui.click('新建空白'); ui.click('确认继续'); wait_preview()
    diagnostic({'camera':[0,90,2], 'pan':[0,0]}); time.sleep(.5)
    ui.click('放置'); click_point((12.5,0,12.5)); wait_preview()
    before = diagnostic(); assert before['blocks']==1,before
    target_node = pointer()['id']
    native_before = ui.call('native_control', target_node)['result']
    box = pointer()['layout']; root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    window = capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left,top,width,height = capture._window_rect(window['hwnd'])
    scale = width/root['width']
    target = (int(left+(box['x']+box['width']/2)*scale), int(top+(box['y']+box['height']/2)*scale))
    capture.user32.SetCursorPos(*target)
    time.sleep(.3)
    interval = float(sys.argv[1]) if len(sys.argv)>1 else .25
    start = time.perf_counter()
    try:
        for unused in range(40):
            assert capture.user32.GetForegroundWindow() == window['hwnd']
            capture.user32.SetCursorPos(*target)
            capture.user32.mouse_event(2,0,0,0,0); time.sleep(interval*.6)
            capture.user32.mouse_event(4,0,0,0,0); time.sleep(interval*.4)
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
    seconds = time.perf_counter()-start
    wait_preview(); after = diagnostic()
    native_after = ui.call('native_control',target_node)['result']
    (ui.OUT/'rapid_native_trace.json').write_text(json.dumps({'before':native_before,'after':native_after},ensure_ascii=False,indent=2),encoding='utf8')
    print('native input counts', native_before.get('globalClickCounts'),native_after.get('globalClickCounts'),flush=True)
    print('rapid result', seconds, before, after, flush=True)
    ui.check('forty native clicks all place across five tile boundaries', after['blocks']==41)
    ui.check('latest selected cell matches the complete stack', after['start']==after['end']==[12,40,12])
    ui.click('历史'); ui.click('撤销'); wait_preview()
    ui.check('last rapid placement has its own undo', diagnostic()['blocks']==40)
    ui.click('参数')
    result = {'checks':ui.checks,'clickSeconds':seconds, 'builds':after['previewBuilds']-before['previewBuilds'],
              'buildSeconds':after['previewSeconds']-before['previewSeconds'], 'before':before,'after':after}
    (ui.OUT/'rapid_placement.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
