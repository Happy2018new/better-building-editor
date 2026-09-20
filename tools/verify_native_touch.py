"""F11 native touch regression; restore the original input mode in finally."""
import json
import ctypes
from ctypes import wintypes
import time
import verify_ui as ui
import capture_screen as capture
from native_input_mode import set_touch, state as input_state
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import pointer
from verify_global_cursor import screen_point


def sustained_drag(fixture):
    """Cross multiple gizmo depth changes while held, pause, then reverse."""
    diagnostic({'fixture': fixture, 'size': [8, 8, 8], 'camera': [0, 20, 1]})
    wait_preview(); ui.click('放置')
    target = pointer(); box = target['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left, top, width, unused = capture._window_rect(window['hwnd'])
    scale = width / root['width']
    sx = int(left + (box['x'] + box['width'] * .5) * scale)
    sy = int(top + (box['y'] + box['height'] * .5) * scale)
    extent = min(75., box['width'] * .28) * scale
    gizmo = ui.nodes('OrientationGizmo')[0]
    tips = [n for n in ui.nodes('Image', gizmo) if str(n.get('key', '')).startswith('tip')]
    tip_before = [ui.call('native_control', n['id'])['result']['position'] for n in tips]
    before = diagnostic(); previous_yaw = before['pose'][0]
    samples = []
    capture.user32.SetCursorPos(sx, sy); time.sleep(.15)
    capture.user32.mouse_event(2, 0, 0, 0, 0)
    try:
        for i in range(1, 91):
            assert capture.user32.GetForegroundWindow() == window['hwnd'], 'Game lost foreground'
            amount = i / 30. if i <= 30 else 2. - i / 30.
            x, y = int(sx + extent * amount), int(sy + scale * i / 15.)
            capture.user32.SetCursorPos(x, y); time.sleep(.025)
            if i % 10 == 0:
                point = wintypes.POINT(); capture.user32.GetCursorPos(ctypes.byref(point))
                assert abs(point.x-x) <= 2 and abs(point.y-y) <= 2, 'Pointer moved outside test control'
                now = diagnostic()
                native = ui.call('native_control', target['id'])['result']
                samples.append({'step': i, 'state': now, 'native': native})
                delta = now['pose'][0] - previous_yaw
                print('Held %s %d: yaw %.3f, delta %.3f' % (fixture, i, now['pose'][0], delta), flush=True)
                ui.check('%s held motion %d follows the finger' % (fixture, i), delta < -1 if i <= 30 else delta > 1)
                ui.check('%s held motion %d retains native touch' % (fixture, i),
                         native['pointerPressed'] and not native['pointerPolling'])
                previous_yaw = now['pose'][0]
                if i == 30:
                    time.sleep(.5)
                    ui.check(fixture + ' held pause does not drift', diagnostic()['pose'] == now['pose'])
                    tip_after = [ui.call('native_control', n['id'])['result']['position'] for n in tips]
                    ui.check(fixture + ' orientation gizmo follows the held orbit', len(tips) == 3 and tip_after != tip_before)
    finally:
        capture.user32.mouse_event(4, 0, 0, 0, 0)
        (ui.OUT / ('sustained_touch_%s.json' % fixture)).write_text(json.dumps(samples, indent=2), encoding='utf8')
    time.sleep(.4)
    native = ui.call('native_control', target['id'])['result']; after = diagnostic()
    ui.check(fixture + ' sustained release finishes exactly one orbit',
             not native['pointerPressed'] and not native['pointerPolling'] and
             after['pointerStats'][1] == before['pointerStats'][1] + 1 and
             after['pointerStats'][2] == before['pointerStats'][2] + 1)
    ui.check(fixture + ' orbit does not edit or rebuild block meshes',
             after['blocks'] == before['blocks'] and after['previewBuilds'] == before['previewBuilds'])
    capture.user32.SetCursorPos(sx, sy); time.sleep(.3)
    ui.check(fixture + ' release prevents further pointer following', diagnostic()['pose'] == after['pose'])


def touch(pos, drag=False, inspect_hold=False):
    target=pointer();box=target['layout'];x,y=screen_point(pos)
    root=ui.nodes('SafeArea')[0]['children'][0]['layout']
    window=capture._find_game_window(capture._list_windows(),process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    left,top,width,height=capture._window_rect(window['hwnd']);scale=width/root['width']
    sx,sy=int(left+(box['x']+x)*scale),int(top+(box['y']+y)*scale)
    previous_yaw = diagnostic()['pose'][0]
    capture.user32.SetCursorPos(sx,sy);time.sleep(.12)
    capture.user32.mouse_event(2,0,0,0,0);time.sleep(.1)
    try:
        if inspect_hold:
            native=ui.call('native_control',target['id'])['result']
            ui.check('native touch tracks callbacks without stale mouse coordinates',native['pointerPressed'] and not native['pointerPolling'])
        if drag:
            for i in range(1,16):
                assert capture.user32.GetForegroundWindow()==window['hwnd']
                capture.user32.SetCursorPos(sx+i*6,sy+i*2);time.sleep(.025)
                if i in (5, 10, 15):
                    current_yaw = diagnostic()['pose'][0]
                    ui.check('native touch rotates before release, sample %d' % i, current_yaw < previous_yaw - .25)
                    previous_yaw = current_yaw
    finally:
        capture.user32.mouse_event(4,0,0,0,0)
    time.sleep(.7)
    native=ui.call('native_control',target['id'])['result']
    ui.check('native touch release ends capture',not native['pointerPressed'] and not native['pointerPolling'])


def verify():
    capture.user32.SetProcessDPIAware()
    assert diagnostic()["touch"], "Enable native touch mode with the workspace closed, then reopen it before this test."
    sustained_drag('solid')
    sustained_drag('demo_large')
    diagnostic({'fixture':'offset'});wait_preview();ui.click('俯视')
    ui.check('manual input toggle and action confirmation are absent',not any(s in ui.labels() for s in ('触控放置','确认放置','确认擦除','确认换材质')))
    ui.click('放置');before=diagnostic()
    touch((3.5,4.,5.5),inspect_hold=True);wait_preview();after=diagnostic()
    if after['blocks']!=before['blocks']+1: print('native touch states',before,after,flush=True)
    ui.check('one native tap directly places exactly one cell',after['blocks']==before['blocks']+1 and after['focused']==[3,4,5])
    touch((3.5,5.,5.5));wait_preview()
    ui.check('consecutive native taps place without confirmation',diagnostic()['blocks']==before['blocks']+2)
    state=diagnostic();touch((3.5,6.,5.5),drag=True);time.sleep(1.2)
    ui.check('native drag rotates without placing a cell',diagnostic()['blocks']==state['blocks'] and diagnostic()['pose'][:2]!=state['pose'][:2])
    settled=diagnostic()['pose']
    capture.user32.SetCursorPos(100,100);time.sleep(.3)
    ui.check('released touch cannot resume orbit on mouse movement', diagnostic()['pose']==settled)
    ui.click('俯视');ui.click('擦除');ui.click('单格');touch((3.5,6.,5.5));wait_preview()
    ui.check('native tap erases directly in erase mode',diagnostic()['blocks']==before['blocks']+1)
    ui.click('选取');touch((4.5,4.,6.5))
    ui.check('selection mode automatically uses native touch',diagnostic()['focused']==[4,3,6] and diagnostic()['touch'])
    ui.click('吸管');touch((4.5,4.,6.5))
    ui.check('eyedropper works without a touch toggle',diagnostic()['focused']==[4,3,6])
    ui.click('框选');touch((2.5,4.,3.5));touch((5.5,4.,8.5))
    ui.check('two native taps define a single shared box',diagnostic()['selection']==24 and diagnostic()['anchor'] is None)
    ui.click('浏览')


def main():
    original = input_state()['simulated']
    try:
        set_touch(True)
        verify()
    finally:
        set_touch(original)
        (ui.OUT/'native_touch_checks.json').write_text(json.dumps(ui.checks,ensure_ascii=False,indent=2),encoding='utf8')


if __name__=='__main__':main()
