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
    resize = subprocess.run([sys.executable, '-X', 'utf8',
        str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/resize_window.py'), '--preset', '16:9'],
        capture_output=True, check=True, encoding='utf8')
    dimensions = json.loads(resize.stdout)
    assert dimensions['ok'] and dimensions['actualClient'] == [1920, 1080], dimensions
    if '取消' in ui.labels():
        ui.click('取消')
    if '还原视图' in ui.labels():
        ui.click('还原视图')
    ui.click('工作台'); ui.click('浏览'); ui.click('参数')
    if scenario == 'slider':
        interaction.category('cube'); ui.click('空心长方体')
        offset = ui.call('scroll', ui.nodes('ScrollView')[-1]['id'], 10000)['result']['position']
        box = ui.nodes('Slider')[0]['layout']
        points = [(box['x'] + box['width'] * v, box['y'] - offset + box['height'] / 2.) for v in (.1, .9)]
    elif scenario == 'categories':
        current = ui.tree()
        points = []
        for glyph in ('cube', 'brush'):
            target = next(n for n in ui.nodes('Action', current) if n['props'].get('glyph') == glyph
                          and n['props'].get('width') == 40 and n['props'].get('height') == 37)
            box = ui.nodes('Button', target)[0]['layout']
            points.append((box['x'] + box['width'] / 2., box['y'] + box['height'] / 2.))
    else:
        current = ui.tree()
        labels = {'segments': ('选取', '浏览'), 'pages': ('建筑库', '工作台'),
                  'pages_all': ('建筑库', '入门指南', '投影', '工作台'),
                  'inspector': ('图层', '参数'), 'history': ('历史', '参数'),
                  'views': ('单层', '完整'), 'depth': ('前移', '后移')}[scenario]
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
    capture.user32.WindowFromPoint.argtypes = [capture.POINT]
    capture.user32.WindowFromPoint.restype = capture.wintypes.HWND
    capture.user32.GetAncestor.argtypes = [capture.wintypes.HWND, capture.wintypes.UINT]
    capture.user32.GetAncestor.restype = capture.wintypes.HWND
    for point in points:
        hit_window = capture.user32.WindowFromPoint(capture.POINT(*point))
        assert capture.user32.GetAncestor(hit_window, 2) == hwnd, 'Another window covers the workload target'
    before = None
    if scenario == 'depth':
        from verify_selection_scope import diagnostic
        before = diagnostic()
    output = ui.OUT / ('controls_%s_%s.json' % (scenario, label))
    with output.open('w', encoding='utf8') as stream:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/tracy.py'),
                                    'capture', '--seconds', '10', '--label', scenario + '_' + label, '--top', '8'], stdout=stream,
                                   creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
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
                    capture.user32.SetCursorPos(*points[index % len(points)]); time.sleep(.12 if scenario=='depth' else .035)
                    capture.user32.mouse_event(2, 0, 0, 0, 0); held = True; time.sleep(.08 if scenario=='depth' else .06)
                    capture.user32.mouse_event(4, 0, 0, 0, 0); held = False
                    index += 1
                else:
                    time.sleep(.01)
        finally:
            if held:
                capture.user32.mouse_event(4, 0, 0, 0, 0)
        process.wait(timeout=35)
    result = json.loads(output.read_text(encoding='utf8'))
    result['workload'] = {'scenario': scenario, 'actualClient': dimensions['actualClient'],
                          'clickIntervalSeconds': .65, 'activeSeconds': 8.}
    if before is not None:
        time.sleep(1.)
        after = diagnostic()
        expected = before['depth']
        step = max(1., max(before['size'])/16.)
        for click_index in range(index):
            expected = max(0., min(sum(before['size'])+1., expected+(step if click_index%2==0 else -step)))
        result['workload'].update(before=before, after=after, clicks=index, expectedDepth=expected)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    if before is not None:
        assert abs(after['depth']-expected)<.001, result['workload']
        assert all(before[k]==after[k] for k in ('pointerStats','pose','previewBuilds','previewExtractions','blocks')), result['workload']
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
