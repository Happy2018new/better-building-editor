"""Verify native input text, clipping, resize and keyboard editing in the game.

Screenshots are diagnostics under ignored .runtime, never UI resources. Draft
text is restored; this check does not save a building or apply world edits.
"""
import json
import subprocess
import sys
import time
import mss
from PIL import Image
import verify_ui as ui
from verify_world_tools import game
import capture_screen as capture
from verify_entry import key
from _protocol import request


def close_workspace():
    # Popping the last screen can stop its clipboard poller before the close
    # acknowledgement is visible. The subsequent reopen and field checks
    # verify the actual lifecycle, including a possible lost acknowledgement.
    result = request('navigator', value={'action': 'close'}, timeout=3.)
    if result and result.get('error'):
        raise AssertionError(result)


def resize(size):
    result = subprocess.run([sys.executable, '-X', 'utf8', str(ui.ROOT /
        '.agents/skills/pyreact-debugging/scripts/resize_window.py'), '--size', size],
        capture_output=True, check=True, encoding='utf8')
    dimensions = json.loads(result.stdout)
    assert dimensions['ok'] and dimensions['actualClient'] == dimensions['requestedClient']
    time.sleep(.4)


def inspect(field, name):
    native = ui.call('native_control', field['id'])['result']
    clip, label = native['clipper'], native['displayText']
    cy, ch = clip['global'][1], clip['size'][1]
    ty, th = label['global'][1], label['size'][1]
    ui.check(name + ': whole native text line fits vertically',
             ty >= cy - .01 and ty + th <= cy + ch + .01)
    ui.check(name + ': clipping remains inside the field',
             abs(cy - native['global'][1]) < .01 and abs(ch - native['size'][1]) < .01 and
             clip['size'][0] <= native['size'][0])
    ui.check(name + ': native text matches controlled value', native['text'] == field['props']['value'])
    metrics = native['screenMetrics']
    # SDK viewport dimensions are padded to a whole GUI step, while logical
    # screen dimensions are truncated. A Win32-width/root-width ratio is not
    # the native bitmap magnification for non-divisible widths such as 1600.
    gui = round(metrics['physical'][0] / metrics['logical'][0])
    physical = field['props']['fontScale'] * gui
    native['physicalFontScale'] = physical
    ui.check(name + ': original glyph physical magnification is an integer (%0.6f)' % physical,
             physical >= 3 - .0001 and abs(physical-round(physical)) < .0001)
    ui.check(name + ': native label uses the requested integer glyph height',
             abs(label['size'][1]*gui-10*physical)<.01)
    return native


def main():
    capture.user32.SetProcessDPIAware()
    report = {'checks': ui.checks, 'cases': []}
    with mss.MSS() as screen:
        window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
        assert window and not window['minimized']
        hwnd = window['hwnd']

        def geometry():
            root = ui.nodes('SafeArea')[0]['children'][0]['layout']
            left, top, width, height = capture._window_rect(hwnd)
            return left, top, width, height, width / root['width']

        def click_native(x, y):
            assert capture._activate_window(hwnd)
            assert capture.user32.GetForegroundWindow() == hwnd
            left, top, unused_w, unused_h, scale = geometry()
            capture.user32.SetCursorPos(int(left + x * scale), int(top + y * scale))
            time.sleep(.05)
            capture.user32.mouse_event(2, 0, 0, 0, 0)
            try:
                time.sleep(.05)
            finally:
                capture.user32.mouse_event(4, 0, 0, 0, 0)
            time.sleep(.4)

        def blur():
            unused_l, unused_t, unused_w, height, scale = geometry()
            click_native(2, height / scale - 2)

        def snapshot(native, name, full=False):
            assert capture.user32.GetForegroundWindow() == hwnd
            left, top, width, height, scale = geometry()
            raw = screen.grab(dict(left=left, top=top, width=width, height=height))
            frame = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
            if not full:
                x, y = native['global']; w, h = native['size']
                frame = frame.crop((int(x * scale), int(y * scale), int((x + w) * scale), int((y + h) * scale)))
            frame.save(ui.OUT / (name + '.png'))

        # Drop any prior diagnostic SetTextFontSize override. Its runtime scale
        # can compose with the template factor in this engine.
        close_workspace()
        time.sleep(.5)
        game('owner.open_workspace()\n_result=True')
        ui.click('建筑库')
        original = ui.nodes('Input', ui.nodes('Library')[0])[0]['props']['value']
        try:
            sample = '林间白盒 · 建筑练习 ABCxyz 0123456789'
            for size in ('1920x1080', '1280x720', '1366x768', '1600x900', '1440x1080'):
                resize(size)
                ui.click('建筑库')
                field = ui.nodes('Input', ui.nodes('Library')[0])[0]
                ui.call('set_input', field['id'], sample)
                blur()
                fields = ui.nodes('Input', ui.nodes('Library')[0])
                for index, field in enumerate(fields):
                    native = inspect(field, size + ' library %d' % index)
                    report['cases'].append({'size': size, 'field': 'library%d' % index, 'native': native})
                    if index == 0 and size in ('1920x1080', '1280x720'):
                        snapshot(native, 'input_current_' + size)
                ui.click('工作台'); ui.click('放置'); ui.click('参数')
                scroll = ui.nodes('ScrollView', ui.nodes('Parameters')[0])[0]
                ui.call('scroll', scroll['id'], 10000)
                time.sleep(.3)
                picker = ui.nodes('MaterialPicker')[0]
                aux = ui.nodes('Input', picker)[1]
                original_aux = aux['props']['value']
                try:
                    ui.call('set_input', aux['id'], '15')
                    for index, field in enumerate(ui.nodes('Input')):
                        native = inspect(field, size + ' workspace %d' % index)
                        report['cases'].append({'size': size, 'field': 'workspace%d' % index, 'native': native})
                    if size in ('1920x1080', '1280x720'):
                        blur()
                        native = ui.call('native_control', aux['id'])['result']
                        viewport = ui.call('native_control', scroll['id'])['result']
                        ui.check(size + ': auxiliary digits are inside the visible scroll area',
                                 native['global'][1] >= viewport['global'][1] and
                                 native['global'][1] + native['size'][1] <=
                                 viewport['global'][1] + viewport['size'][1])
                        snapshot(native, 'input_aux_' + size)
                        snapshot(native, 'input_workspace_' + size, full=True)
                finally:
                    ui.call('set_input', aux['id'], original_aux)

            resize('1920x1080')
            ui.click('建筑库')
            field = ui.nodes('Input', ui.nodes('Library')[0])[0]
            ui.call('set_input', field['id'], '')
            native = ui.call('native_control', field['id'])['result']
            x, y = native['global']; w, h = native['size']
            click_native(x + w / 2., y + h / 2.)
            def press(code):
                assert capture.user32.GetForegroundWindow() == hwnd
                capture.user32.keybd_event(code, 0, 0, 0)
                try:
                    time.sleep(.06)
                finally:
                    capture.user32.keybd_event(code, 0, 2, 0)
                time.sleep(.12)

            # Keep the user's input method unchanged. ABC may compose Chinese
            # with an active IME; Enter commits before testing native deletion.
            for code in (65, 66, 67, 49, 50, 51, 13):
                press(code)
            time.sleep(.4)
            typed = ui.call('native_control', field['id'])['result']['text']
            ui.check('real keyboard commits text using the current input method', len(typed) >= 2)
            click_native(x + w / 2., y + h / 2.)
            for code in (35, 8, 13):
                press(code)
            blur()
            field = ui.nodes('Input', ui.nodes('Library')[0])[0]
            ui.check('End and Backspace delete the last committed character',
                     field['props']['value'] == typed[:-1])
            inspect(field, 'keyboard result')
            long_text = '中文建筑与标点，。ABCxyz0123456789 / ' * 12
            ui.call('set_input', field['id'], long_text)
            click_native(x + w / 2., y + h / 2.)
            key(hwnd, 35)  # End: native caret scrolls to the trailing text.
            native = ui.call('native_control', field['id'])['result']
            ui.check('long Chinese text survives native caret scrolling', native['text'] == long_text)
            snapshot(native, 'input_long_caret')
            ui.call('set_input', field['id'], original)
            blur()
            close_workspace()
            time.sleep(.5)
            game('owner.open_workspace()\n_result=True')
            ui.click('建筑库')
            field = ui.nodes('Input', ui.nodes('Library')[0])[0]
            native = inspect(field, 'reopened input')
            ui.check('reopened workspace preserves the restored draft name', native['text'] == original)
            snapshot(native, 'input_current_final')
        finally:
            ui.click('建筑库')
            field = ui.nodes('Input', ui.nodes('Library')[0])[0]
            ui.call('set_input', field['id'], original)
            resize('1920x1080')
            (ui.OUT / 'input_scale_checks.json').write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print('%d input checks passed' % len(ui.checks))


if __name__ == '__main__':
    main()
