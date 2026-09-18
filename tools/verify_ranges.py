"""Read native progress geometry after dragging, pane changes and resize."""
import json
import subprocess
import sys
import time
import verify_ui as ui
from verify_interaction import category


def check_fill(expected):
    control = next(n for n in ui.nodes('Range') if n['props']['label'] == '厚度')
    images = ui.nodes('Image', control)
    track = next(n for n in images if n.get('style', {}).get('zIndex') == 1)
    fill = next(n for n in images if n.get('style', {}).get('zIndex') == 2)
    knob = next(n for n in images if n.get('style', {}).get('zIndex') == 3)
    t, f, k = [ui.call('native_control', n['id'])['result'] for n in (track, fill, knob)]
    assert abs(f['size'][0] - t['size'][0] * expected) < .05, (t, f, expected)
    assert abs(f['global'][0] - t['global'][0]) < .05
    assert abs(k['global'][0] + k['size'][0] / 2. - t['global'][0] - f['size'][0]) < .2


def main():
    ui.click('工作台'); ui.click('三维'); ui.click('参数')
    category('cube'); ui.click('空心长方体')
    for value in (0., 5./7., 1., 2./7.):
        ui.call('set_slider', ui.nodes('Slider')[0]['id'], value)
        time.sleep(.4)
        check_fill(value)
        ui.check('progress and thumb agree at %.3f' % value, True)
    ui.click('图层'); ui.click('历史'); ui.click('参数')
    check_fill(2./7.)
    ui.check('fill survives retained pane switches', True)
    for size in ('1280x720', '1440x1080', '1920x1080'):
        raw = subprocess.check_output([sys.executable, '-X', 'utf8', str(ui.ROOT /
            '.agents/skills/pyreact-debugging/scripts/resize_window.py'), '--size', size], encoding='utf8')
        result = json.loads(raw)
        assert result['ok'] and result['actualClient'] == result['requestedClient']
        time.sleep(.5)
        check_fill(2./7.)
        ui.check(size + ' preserves progress and thumb alignment', True)
    ui.call('set_slider', ui.nodes('Slider')[0]['id'], 5./7.)
    time.sleep(.4)
    ui.call('scroll', ui.nodes('ScrollView')[-1]['id'], 10000)
    (ui.OUT / 'range_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
