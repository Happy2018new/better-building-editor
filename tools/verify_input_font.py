"""Compare native input glyphs with font batching on/off/on; never change fonts.

Requires the running development UI, pyperclip, mss and Pillow. All screenshots
are diagnostic output under .runtime; no resource-pack images are created.
The SDK exposes no getter. This experiment restores its documented default
(enabled) in finally, and restores the original draft name without saving it.
"""
import argparse
import json
import subprocess
import sys
import time
import mss
from PIL import Image, ImageChops
import verify_ui as ui
from verify_world_tools import game
import capture_screen as capture
from verify_entry import key


def changed_pixels(a, b):
    assert a.size == b.size, 'Compared input boxes must have identical dimensions'
    diff = ImageChops.difference(a, b)
    return {'changedPixels': sum(pixel != (0, 0, 0) for pixel in diff.getdata()),
            'bounds': diff.getbbox()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remount', action='store_true', help='Reopen the workspace after each API call')
    args = parser.parse_args()
    capture.user32.SetProcessDPIAware()
    # MSS establishes DPI awareness before any UI-to-pixel conversion.
    with mss.MSS() as screen:
        resize = subprocess.run([sys.executable, '-X', 'utf8',
            str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/resize_window.py'), '--preset', '16:9'],
            capture_output=True, check=True, encoding='utf8')
        dimensions = json.loads(resize.stdout)
        assert dimensions['ok'] and dimensions['actualClient'] == [1920, 1080]
        window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
        assert window
        hwnd = window['hwnd']
        ui.click('建筑库')
        field = ui.nodes('Input', ui.nodes('Library')[0])[0]
        original = field['props']['value']
        sample = '林间白盒 · 建筑练习'
        mode = 'remount' if args.remount else 'live'
        report = {'mode': mode, 'sample': sample, 'client': dimensions['actualClient'],
                  'cases': [], 'checks': ui.checks}
        frames = []
        try:
            ui.call('set_input', field['id'], sample)
            time.sleep(.3)
            for name, enabled in [('on', True), ('off', False), ('on_again', True)]:
                response = ui.call('font_batch', value=enabled)['result']
                if args.remount:
                    ui.call('navigator', value={'action': 'close'})
                    time.sleep(.4)
                    game('owner.open_workspace()\n_result=True')
                    ui.click('建筑库')
                    field = ui.nodes('Input', ui.nodes('Library')[0])[0]
                native = ui.call('native_control', field['id'])['result']
                root = ui.nodes('SafeArea')[0]['children'][0]['layout']
                ui.check(name + ': native input preserves Chinese text', native['text'] == sample)
                assert capture._activate_window(hwnd)
                left, top, width, height = capture._window_rect(hwnd)
                scale = width / root['width']
                # Blur using a real click in the status bar; wait for flecks to
                # expire. This excludes caret blinking from the pixel comparison.
                capture.user32.SetCursorPos(left + 8, top + height - 8)
                capture.user32.mouse_event(2, 0, 0, 0, 0)
                try:
                    time.sleep(.05)
                finally:
                    capture.user32.mouse_event(4, 0, 0, 0, 0)
                time.sleep(.6)
                assert capture.user32.GetForegroundWindow() == hwnd
                raw = screen.grab(dict(left=left, top=top, width=width, height=height))
                image = Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
                x, y = native['global']
                w, h = native['size']
                crop = image.crop((int(x * scale), int(y * scale), int((x + w) * scale), int((y + h) * scale)))
                output = ui.OUT / ('input_font_%s_%s.png' % (mode, name))
                crop.save(output)
                frames.append(crop)
                report['cases'].append({'batchRequested': enabled, 'api': response,
                                        'native': native, 'screenshot': str(output)})
            report['onOffDifference'] = changed_pixels(frames[0], frames[1])
            report['onOnDifference'] = changed_pixels(frames[0], frames[2])
            boxes = [(case['native']['global'], case['native']['size']) for case in report['cases']]
            ui.check('font batching does not move or resize the input', all(box == boxes[0] for box in boxes))
        finally:
            ui.call('font_batch', value=True)
            field = ui.nodes('Input', ui.nodes('Library')[0])[0]
            ui.call('set_input', field['id'], original)
        (ui.OUT / ('input_font_%s.json' % mode)).write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
        print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
