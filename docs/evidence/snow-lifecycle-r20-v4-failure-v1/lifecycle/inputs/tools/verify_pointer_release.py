"""Stress actual native mouse capture, fast clicks and release outside the viewport."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_interaction import pointer, point
from verify_selection_scope import diagnostic, wait_preview


def main():
    capture.user32.SetProcessDPIAware()
    ui.click('工作台')
    diagnostic({'fixture': 'demo', 'camera': [35, 25, 1]})
    wait_preview()
    ui.click('浏览')
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    hwnd = window['hwnd']
    left, top, width, height = capture._window_rect(hwnd)
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    scale = width / root['width']
    target = pointer()
    box = target['layout']
    x, y = box['x'] + box['width'] / 2., box['y'] + box['height'] / 2.

    def move(px, py):
        assert capture.user32.GetForegroundWindow() == hwnd
        capture.user32.SetCursorPos(int(left + px * scale), int(top + py * scale))

    def held():
        native = ui.call('native_control', target['id'])['result']
        return native['pointerPressed'] or native['pointerPolling']

    def idle_motion(name):
        time.sleep(1.8)  # Allow the intentionally bounded camera inertia to end.
        before = diagnostic()['pose']
        for index in range(12):
            move(x + (index % 3 - 1) * 14, y + (index % 4 - 2) * 8)
            time.sleep(.015)
        time.sleep(.2)
        after = diagnostic()['pose']
        ui.check(name, not held() and max(abs(a-b) for a,b in zip(before, after)) < .05)

    try:
        move(x, y)
        time.sleep(.15)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(.12)
        ui.check('native press starts capture', held())
        for i in range(10):
            move(x + i * 2, y - i)
            time.sleep(.018)
        capture.user32.mouse_event(4, 0, 0, 0, 0)
        idle_motion('release stops tracking and subsequent hover does not rotate')

        for hold in (.001, .008, .02, .045):
            for i in range(20):
                move(x + (i % 4) * 2, y + (i % 3) * 2)
                capture.user32.mouse_event(2, 0, 0, 0, 0)
                time.sleep(hold)
                capture.user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(hold)
            idle_motion('20 rapid clicks at %.3fs leave no capture' % hold)

        move(x, y)
        time.sleep(.12)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(.1)
        move(box['x'] + box['width'] + 8, y)
        time.sleep(.15)
        ui.check('leaving the viewport cancels capture while held', not held())
        capture.user32.mouse_event(4, 0, 0, 0, 0)
        move(x, y)
        idle_motion('release outside and reentry do not restart orbit')

        move(x, y)
        time.sleep(.12)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        time.sleep(.1)
        ui.click('建筑库')
        ui.check('hidden viewport cancels capture', not held())
        capture.user32.mouse_event(4, 0, 0, 0, 0)
        ui.click('工作台')
        idle_motion('returning from another page cannot resume an old drag')

        diagnostic({'camera': [0, 90, 1]})
        time.sleep(.8)
        for hold in (.03, .06, .1):
            for index in range(6):
                cell = (20, 5, 3) if index % 2 else (8, 10, 14)
                px, py = point((cell[0] + .5, cell[1] + 1., cell[2] + .5))
                move(box['x'] + px, box['y'] + py)
                time.sleep(.12)
                capture.user32.mouse_event(2, 0, 0, 0, 0)
                time.sleep(hold)
                capture.user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(.3)
                ui.check('%.3fs click %d selects its new target' % (hold, index + 1),
                         diagnostic()['focused'] == list(cell) and not held())
    finally:
        capture.user32.mouse_event(4, 0, 0, 0, 0)
    (ui.OUT / 'pointer_release_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
