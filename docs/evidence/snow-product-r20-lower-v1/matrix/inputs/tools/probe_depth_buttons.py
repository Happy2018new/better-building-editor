"""Strict native short-press probe; still fails intermittently on large 3.9 previews."""
import json
import sys
import time
import verify_ui as ui
import capture_screen as capture
from simulate import _resolve_label
from verify_selection_scope import diagnostic, wait_preview


def settled():
    for unused in range(120):
        time.sleep(.2)
        state = diagnostic()
        if abs(state['depth']-state['depthTarget'])<.001:
            return state
    raise AssertionError('depth animation did not settle')


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and window['process'] == 'Minecraft.Windows.exe'
    assert capture._activate_window(window['hwnd'])
    left, top, width, unused = capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left+20, top+20)
    ui.click('工作台'); ui.click('完整'); ui.click('浏览')
    # An empty -> nonempty transition used to move unkeyed overlays, clear the
    # navigation ref and let the screen-wide pointer fallback steal the click.
    if '--current' not in sys.argv:
        ui.new_region((64,128,64)); wait_preview()
        diagnostic({'fixture':'interior', 'size':[64,128,64]}); wait_preview()
        for unused in range(8):
            ui.click('前移')
    else:
        state = diagnostic()
        assert state['size']==[64,128,64] and state['blocks']==39945, state
    current = ui.tree()
    scale = width/ui.nodes('SafeArea',current)[0]['children'][0]['layout']['width']
    points = []
    for label in ('前移','后移'):
        node = next(n for n in _resolve_label(current,label) if label in ui.labels(n))
        native = ui.call('native_control',node['id'])['result']
        points.append((int(left+(native['global'][0]+native['size'][0]/2.)*scale),
                       int(top+(native['global'][1]+native['size'][1]/2.)*scale)))
    before = settled()
    held = False
    try:
        for index in range(20):
            assert capture.user32.GetForegroundWindow() == window['hwnd']
            capture.user32.SetCursorPos(*points[index%2]); time.sleep(.035)
            capture.user32.mouse_event(2,0,0,0,0); held=True; time.sleep(.06)
            capture.user32.mouse_event(4,0,0,0,0); held=False; time.sleep(.555)
    finally:
        if held:
            capture.user32.mouse_event(4,0,0,0,0)
    after = settled()
    report = {'checks':ui.checks,'before':before,'after':after,
              'cursorSettleSeconds':.035,'pressSeconds':.06,'clickIntervalSeconds':.65}
    output = ui.OUT/'depth_button_checks_32.json'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    ui.check('twenty alternating native depth clicks return to the same depth',
             abs(after['depth']-before['depthTarget']) < .001)
    ui.check('navigation never starts a scene press',after['pointerStats']==before['pointerStats'])
    ui.check('depth navigation retains scale, data and all cached geometry',
             all(before[k]==after[k] for k in ('pose','blocks','previewBuilds','previewExtractions')))
    # Equal forward/back losses could cancel numerically; verify a one-way run.
    for unused in range(4):
        capture.user32.SetCursorPos(*points[0]); time.sleep(.035)
        try:
            capture.user32.mouse_event(2,0,0,0,0); time.sleep(.06)
        finally:
            capture.user32.mouse_event(4,0,0,0,0)
        time.sleep(.555)
    end = settled()
    ui.check('four native forward clicks each advance eight blocks',abs(end['depth']-before['depthTarget']-32.)<.001)
    ui.check('one-way navigation also avoids scene edits and submissions',
             all(end[k]==before[k] for k in ('pointerStats','blocks','previewBuilds','previewExtractions')))
    report['end'] = end
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':
    main()
