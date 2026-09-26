"""Rapid native F11 touch taps at distinct viewport positions."""
import json
import sys
import time

import verify_ui as ui
import capture_screen as capture
from native_input_mode import open_workspace, set_touch, state
from verify_interaction import pointer
from verify_selection_scope import diagnostic, wait_preview
from verify_world_tools import game


def main():
    original = state()['simulated']
    open_workspace()
    try:
        window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
        assert window and capture._activate_window(window['hwnd'])
        set_touch(True)
        game('s.set("page","workspace")\ns.choose_mode("browse")\n_result=True')
        diagnostic({'fixture': 'offset', 'camera': [35, 25, 1]})
        wait_preview()
        target = pointer()
        bounds = target['layout']
        root = ui.nodes('SafeArea')[0]['children'][0]['layout']
        assert capture._activate_window(window['hwnd'])
        left, top, width, unused = capture._window_rect(window['hwnd'])
        scale = width / root['width']
        before = diagnostic()
        assert not game('_result=s.camera_dragging')
        game('''h=api.GetTopScreen()
t=next(t for t in h._projection_pointer_surfaces if t.props.get('onPinch'))
api._mobile_touch_trace=[]
api._mobile_touch_send=t.send
def mobile_trace_send(name,args):
 api._mobile_touch_trace.append((name,args.get('TouchId'),args.get('TouchEvent'),
     args.get('TouchPosX'),args.get('TouchPosY'),t.pressed))
 return api._mobile_touch_send(name,args)
t.send=mobile_trace_send
_result=True''')
        points = ((.35,.43),(.58,.52),(.42,.62),(.62,.39),(.46,.48),(.54,.58))
        for index in range(36):
            px, py = points[index % len(points)]
            x = int(left + (bounds['x'] + bounds['width'] * px) * scale)
            y = int(top + (bounds['y'] + bounds['height'] * py) * scale)
            assert capture.user32.GetForegroundWindow() == window['hwnd']
            capture.user32.SetCursorPos(x, y)
            capture.user32.mouse_event(2, 0, 0, 0, 0)
            time.sleep(.025)
            capture.user32.mouse_event(4, 0, 0, 0, 0)
            time.sleep(.025)
        time.sleep(.35)
        after = diagnostic()
        native = ui.call('native_control', target['id'])['result']
        print('native rapid state: before=%s after=%s pose=%s -> %s pressed=%s dragging=%s' %
              (before['pointerStats'], after['pointerStats'], before['pose'], after['pose'],
               native['pointerPressed'], game('_result=s.camera_dragging')), flush=True)
        trace = game('_result=api._mobile_touch_trace')
        (ui.OUT / 'mobile_touch_trace.json').write_text(json.dumps(trace, indent=2), encoding='utf8')
        down_count = after['pointerStats'][0] - before['pointerStats'][0]
        up_count = after['pointerStats'][1] - before['pointerStats'][1]
        ui.check('native taps that reach viewport all finish once',
                 down_count == up_count and down_count >= 18)
        ui.check('rapid taps leave camera idle and stationary',
                 after['pose'] == before['pose'] and
                 not native['pointerPressed'] and not native['pointerPolling'] and
                 not game('_result=s.camera_dragging'))
        print('rapid touches: %s -> %s' % (before['pointerStats'], after['pointerStats']), flush=True)
        if '--full' in sys.argv:
            from verify_native_touch import verify
            verify()
    finally:
        capture.user32.mouse_event(4, 0, 0, 0, 0)
        game('''if hasattr(api,'_mobile_touch_send'):
 t.send=api._mobile_touch_send
_result=True''')
        set_touch(original)
        game('''from modern_projection.pyreact import navigator
if navigator.contains('modern_projection_workspace'):navigator.pop()
_result=True''')


if __name__ == '__main__':
    main()
