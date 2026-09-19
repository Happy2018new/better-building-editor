"""Repeatable ten-second native orbit/wheel workload with Tracy capture."""
import json
import math
import subprocess
import sys
import time
import verify_ui as ui
import verify_interaction as interaction
import capture_screen as capture


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else 'viewport'
    ui.click('工作台'); ui.click('浏览')
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id'])
    time.sleep(.8)
    box = interaction.pointer()['layout']
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    (ui.OUT / ('profile_' + label + '_layout.json')).write_text(json.dumps({'viewport': box, 'root': root}, indent=2), encoding='utf8')
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    hwnd = window['hwnd']
    left, top, width, unused = capture._window_rect(hwnd)
    scale = width / root['width']
    x, y = left + (box['x'] + box['width'] / 2) * scale, top + (box['y'] + box['height'] / 2) * scale
    capture.user32.SetCursorPos(int(x), int(y)); time.sleep(.2)
    output = ui.OUT / ('profile_' + label + '.json')
    with output.open('w', encoding='utf8') as stream:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/tracy.py'),
                                    'capture', '--seconds', '10', '--label', label, '--top', '10'], stdout=stream,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
        time.sleep(1.)
        start = time.perf_counter()
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        try:
            while time.perf_counter() - start < 6.:
                assert capture.user32.GetForegroundWindow() == hwnd
                t = time.perf_counter() - start
                capture.user32.SetCursorPos(int(x + 110 * math.sin(t * 2)), int(y + 55 * math.sin(t * 3)))
                time.sleep(1. / 120.)
        finally:
            capture.user32.mouse_event(4, 0, 0, 0, 0)
        for i in range(14):
            assert capture.user32.GetForegroundWindow() == hwnd
            capture.user32.mouse_event(0x0800, 0, 0, 120 if i < 7 else -120, 0)
            time.sleep(.16)
        process.wait(timeout=35)
    result = json.loads(output.read_text(encoding='utf8'))
    result['workload'] = {'complete': True, 'scenario': 'native orbit and wheel',
                          'clientWidth': width, 'orbitSeconds': 6., 'wheelEvents': 14}
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(output.read_text(encoding='utf8'))


if __name__ == '__main__':
    main()
