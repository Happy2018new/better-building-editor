"""Real page clicks: burst coordinates, bounded pool, and input transparency."""
import json
import time
import mss
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_motion import fast
from simulate import _resolve_label


def main():
    if '取消' in ui.labels():
        ui.click('取消')
    ui.click('工作台'); ui.click('浏览')
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    hwnd = window['hwnd']
    assert capture._activate_window(hwnd)
    capture.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0001 | 0x0004)
    capture.user32.WindowFromPoint.argtypes = [capture.POINT]
    capture.user32.WindowFromPoint.restype = capture.wintypes.HWND
    capture.user32.GetAncestor.argtypes = [capture.wintypes.HWND, capture.wintypes.UINT]
    capture.user32.GetAncestor.restype = capture.wintypes.HWND
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    left, top, pixel_w, pixel_h = capture._window_rect(hwnd)
    scale = pixel_w / root['width']
    effect = ui.nodes('ClickEffects', ui.call('dump_tree')['tree'])[0]
    refs = ui.nodes('Image', effect)
    identities = [n['id'] for n in refs]
    screen = mss.MSS()

    def native_click(x, y, inspect=True, require_visible=True):
        assert capture.user32.GetForegroundWindow() == hwnd
        point = (int(left + x * scale), int(top + y * scale))
        hit = capture.user32.WindowFromPoint(capture.POINT(*point))
        assert capture.user32.GetAncestor(hit, 2) == hwnd, 'Another window covers the click'
        capture.user32.SetCursorPos(*point)
        time.sleep(.035)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        try:
            time.sleep(.05)
        finally:
            capture.user32.mouse_event(4, 0, 0, 0, 0)
        if not inspect:
            return
        # Six clipboard round trips can exceed a 480 ms burst. Capture pixels
        # first, then read retained emission coordinates without timing races.
        raw = screen.grab(dict(left=max(left, point[0]-95), top=max(top, point[1]-95),
                              width=190, height=190))
        pixels = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
        ink = sum(1 for r, g, b in pixels.getdata() if (b-r > 60 and b-g > 30) or (g-r > 60 and b-r > 60))
        states = [fast('native_control', n['id'])['result'] for n in refs]
        hit = [s for s in states if abs(s['global'][0] + s['size'][0] / 2. - x) < 1 and
               abs(s['global'][1] + s['size'][1] / 2. - y) < 1]
        assert hit, (x, y, states)
        assert not require_visible or ink > 30, (x, y, ink)
        assert hit[0]['size'][0] * scale > 140, hit[0]
        return hit[0]

    def click_label(label, require_visible=False):
        current = ui.tree()
        node = next(n for n in _resolve_label(current, label) if label in ui.labels(n))
        box = node['layout']
        native_click(box['x'] + box['width'] / 2., box['y'] + box['height'] / 2., require_visible=require_visible)
        time.sleep(.4)

    x, y = root['width'] * .46, 13.
    native_click(x, y)
    ui.check('blank header produces a large burst at the actual pointer', True)
    click_label('建筑库')
    ui.check('global feedback does not swallow page buttons', bool(ui.nodes('Library')))
    click_label('工作台')
    field = ui.nodes('Input', ui.nodes('ToolList')[0])[0]
    ui.call('set_input', field['id'], '')
    box = field['layout']
    native_click(box['x'] + box['width'] / 2., box['y'] + box['height'] / 2.)
    for key in (70, 73, 76, 76):
        capture.user32.keybd_event(key, 0, 0, 0)
        time.sleep(.04)
        capture.user32.keybd_event(key, 0, 2, 0)
        time.sleep(.15)
    capture.user32.keybd_event(13, 0, 0, 0)
    time.sleep(.08)
    capture.user32.keybd_event(13, 0, 2, 0)
    until = time.monotonic() + 3
    typed = ''
    while time.monotonic() < until:
        typed = ui.nodes('Input', ui.nodes('ToolList')[0])[0]['props']['value']
        if typed == 'fill':
            break
        time.sleep(.1)
    ui.check('global feedback preserves native input focus and typing', typed == 'fill')
    ui.call('set_input', field['id'], '')
    # Creating the modal can exceed one burst lifetime on a cold first mount.
    # Inspect its emission coordinates, then sample a live burst over the modal.
    click_label('读取选区', require_visible=False)
    native_click(x, y)
    ui.check('burst renders above the dialog and its scrim stays active', '请确认这次操作' in ui.labels())
    click_label('取消')
    ui.check('native dialog cancel remains clickable', '请确认这次操作' not in ui.labels())
    for unused in range(12):
        native_click(x, y, inspect=False)
    current = ui.nodes('ClickEffects', ui.call('dump_tree')['tree'])[0]
    ui.check('rapid clicks reuse the same six native sprites', identities == [n['id'] for n in ui.nodes('Image', current)])
    time.sleep(.6)
    ui.check('all burst sprites retire after the animation', not any(fast('native_control', n['id'])['result']['visible'] for n in refs))
    ui.click('入门指南'); ui.click('减少动态效果')
    native_click(x, y, inspect=False)
    ui.check('reduced motion suppresses global particles', not any(fast('native_control', n['id'])['result']['visible'] for n in refs))
    ui.click('减少动态效果'); ui.click('工作台')
    # Actual pixels matter for visibility; capture only the verified game region.
    native_click(root['width'] * .52, root['height'] * .32, inspect=False)
    time.sleep(.08)
    raw = screen.grab(dict(left=left, top=top, width=pixel_w, height=pixel_h))
    Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX').save(ui.OUT / 'click_effect_actual.png')
    time.sleep(.6)
    close = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'close')
    ui.call('click', ui.nodes('Button', close)[0]['id'])
    time.sleep(.6)
    assert capture._activate_window(hwnd)
    capture.user32.keybd_event(80, 0, 0, 0)
    time.sleep(.08)
    capture.user32.keybd_event(80, 0, 2, 0)
    time.sleep(.8)
    effect = ui.nodes('ClickEffects', ui.call('dump_tree')['tree'])[0]
    refs = ui.nodes('Image', effect)
    native_click(x, y)
    ui.check('closing and reopening rebinds exactly one effect pool', len(refs) == 6)
    screen.close()
    (ui.OUT / 'click_effect_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
