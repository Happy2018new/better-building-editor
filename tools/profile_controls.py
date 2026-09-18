"""Ten-second native slider/option/page workloads; no clipboard traffic during sampling."""
import json
import math
import subprocess
import sys
import time
import verify_ui as ui
import verify_interaction as interaction
import capture_screen as capture
from simulate import _resolve_label


def main():
    scenario, label = sys.argv[1:3]
    if '取消' in ui.labels():
        ui.click('取消')
    if '还原视图' in ui.labels():
        ui.click('还原视图')
    ui.click('工作台'); ui.click('浏览')
    if scenario == 'slider':
        interaction.category('cube'); ui.click('空心长方体')
        offset = ui.call('scroll', ui.nodes('ScrollView')[-1]['id'], 10000)['result']['position']
        box = ui.nodes('Slider')[0]['layout']
        points = [(box['x'] + box['width'] * v, box['y'] - offset + box['height'] / 2.) for v in (.1, .9)]
    else:
        current = ui.tree()
        labels = ('选取', '浏览') if scenario == 'segments' else ('建筑库', '工作台')
        points = []
        for label_text in labels:
            target = next(n for n in _resolve_label(current, label_text) if label_text in ui.labels(n))
            box = target['layout']
            points.append((box['x'] + box['width'] / 2., box['y'] + box['height'] / 2.))
    root = ui.nodes('SafeArea')[0]['children'][0]['layout']
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    hwnd = window['hwnd']
    left, top, width, unused = capture._window_rect(hwnd)
    scale = width / root['width']
    points = [(int(left + x * scale), int(top + y * scale)) for x, y in points]
    output = ui.OUT / ('controls_%s_%s.json' % (scenario, label))
    with output.open('w', encoding='utf8') as stream:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/tracy.py'),
                                    'capture', '--seconds', '10', '--label', scenario + '_' + label, '--top', '8'], stdout=stream)
        time.sleep(1.)
        capture.user32.SetCursorPos(*points[0]); time.sleep(.15)
        start = time.perf_counter()
        held = False
        try:
            if scenario == 'slider':
                capture.user32.mouse_event(2, 0, 0, 0, 0); held = True
            index = 0
            while time.perf_counter() - start < 8.:
                assert capture.user32.GetForegroundWindow() == hwnd
                elapsed = time.perf_counter() - start
                if scenario == 'slider':
                    fraction = .5 - .5 * math.cos(elapsed * 3.)
                    x = points[0][0] + (points[1][0] - points[0][0]) * fraction
                    capture.user32.SetCursorPos(int(x), points[0][1]); time.sleep(1. / 90.)
                elif elapsed >= index * .65:
                    capture.user32.SetCursorPos(*points[index % 2]); time.sleep(.035)
                    capture.user32.mouse_event(2, 0, 0, 0, 0); held = True; time.sleep(.06)
                    capture.user32.mouse_event(4, 0, 0, 0, 0); held = False
                    index += 1
                else:
                    time.sleep(.01)
        finally:
            if held:
                capture.user32.mouse_event(4, 0, 0, 0, 0)
        process.wait(timeout=35)
    print(output.read_text(encoding='utf8'))


if __name__ == '__main__':
    main()
