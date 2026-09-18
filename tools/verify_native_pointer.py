"""Exercise the actual game's mouse bindings; never click a different window."""
import json
import time
import verify_interaction as interaction
import verify_ui as ui
import capture_screen as capture


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and not window['minimized']
    hwnd = window['hwnd']

    def move(x, y):
        assert capture._activate_window(hwnd)
        assert capture.user32.GetForegroundWindow() == hwnd
        left, top, pixel_w, unused = capture._window_rect(hwnd)
        root = ui.nodes('SafeArea')[0]['children'][0]['layout']
        assert 0 <= x < root['width'] and 0 <= y < root['height'], 'Pointer must stay inside the game client'
        scale = pixel_w / root['width']
        capture.user32.SetCursorPos(int(left + x * scale), int(top + y * scale))
        time.sleep(.12)
        assert capture.user32.GetForegroundWindow() == hwnd

    def click_at(x, y):
        move(x, y)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        try:
            time.sleep(.06)
        finally:
            capture.user32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(.3)

    ui.click('工作台'); ui.click('浏览')
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id'])
    ui.click('俯视'); time.sleep(.7)
    ui.click('浏览')
    initial_yaw = ui.nodes('PaperDoll')[0]['props']['initRotZ']
    box = interaction.pointer()['layout']
    x, y = interaction.point((20.5, 6., 3.5))
    click_at(box['x'] + x, box['y'] + y)
    ui.check('native mouse picks the visible leaf block', 'X 20 · Y 5 · Z 3' in ui.labels())
    x, y = box['x'] + box['width'] / 2., box['y'] + box['height'] / 2.
    move(x, y)
    # Send real mouse input only while the verified game retains foreground.
    capture.user32.mouse_event(2, 0, 0, 0, 0)
    try:
        left, top, pixel_w, unused = capture._window_rect(hwnd)
        scale = pixel_w / ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
        for i in range(1, 13):
            assert capture.user32.GetForegroundWindow() == hwnd
            capture.user32.SetCursorPos(int(left + (x + i * 1.5) * scale), int(top + (y - i * .7) * scale))
            time.sleep(.02)
    finally:
        capture.user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(.6)
    ui.click('浏览')
    props = ui.nodes('PaperDoll')[0]['props']
    print('Settled native drag angles:', props['initRotZ'], props['initRotX'])
    ui.check('native drag orbits in two axes', 5 < abs(props['initRotZ']) < 60 and props['initRotX'] < -2)
    delta = (props['initRotZ'] - initial_yaw + 180.) % 360. - 180.
    ui.check('rightward native drag rotates the model with the hand', delta < -5.)
    move(x, y)
    time.sleep(.12)
    assert capture.user32.GetForegroundWindow() == hwnd
    capture.user32.mouse_event(0x0800, 0, 0, 120, 0)
    time.sleep(.5)
    ui.check('native wheel zooms the hovered viewport', '112%' in ui.labels())
    interaction.category('cube'); ui.click('空心长方体')
    offset = ui.call('scroll', ui.nodes('ScrollView')[-1]['id'], 10000)['result']['position']
    time.sleep(.2)
    slider = ui.nodes('Slider')[0]['layout']
    click_at(slider['x'] + slider['width'] - .5, slider['y'] - offset + slider['height'] / 2.)
    ui.check('native horizontal slider reaches maximum', '8 格' in ui.labels())
    rail = ui.nodes('Pointer', ui.nodes('Scroll')[-1])[0]['layout']
    click_at(rail['x'] + rail['width'] / 2., rail['y'] + 1.)
    position = ui.call('get_scroll', ui.nodes('ScrollView')[-1]['id'])['result']['position']
    ui.check('native vertical track scrolls to top', abs(position) < 2.)
    x, y = rail['x'] + rail['width'] / 2., rail['y'] + 8.
    move(x, y)
    left, top, pixel_w, unused = capture._window_rect(hwnd)
    scale = pixel_w / ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
    capture.user32.mouse_event(2, 0, 0, 0, 0)
    try:
        time.sleep(.06)
        for i in range(1, 11):
            assert capture.user32.GetForegroundWindow() == hwnd
            capture.user32.SetCursorPos(int(left + x * scale), int(top + (y + i * 5.) * scale))
            time.sleep(.025)
    finally:
        capture.user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(.3)
    position = ui.call('get_scroll', ui.nodes('ScrollView')[-1]['id'])['result']['position']
    ui.check('native scrollbar thumb drags content', position > 30.)
    (ui.OUT / 'native_pointer_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
