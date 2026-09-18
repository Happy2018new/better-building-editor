"""Retained native panes must survive navigation and refresh after editing."""
import json
import time
import verify_ui as ui
from simulate import _walk


def identities(kind):
    # Include inactive panes: they remain mounted but cannot receive input.
    raw = ui.call('dump_tree')['tree']
    component = next(n for n, unused in _walk(raw) if n.get('type') == kind)
    return [n['id'] for n, unused in _walk(component) if n.get('id', '').startswith('__pyr_')]


def main():
    ui.click('工作台'); ui.click('三维'); ui.click('浏览'); ui.click('参数')
    params, layers, history, canvas = [identities(kind) for kind in ('Parameters', 'Layers', 'History', 'LayerCanvas')]
    models = [n['id'] for n in ui.nodes('PaperDoll')]
    view = ui.nodes('ScrollView', ui.nodes('Parameters')[0])[0]
    offset = ui.call('scroll', view['id'], 45)['result']['position']
    for label in ('图层', '历史', '参数', '历史', '图层', '参数'):
        ui.click(label)
    ui.check('all inspector controls are reused across repeated switches',
             [params, layers, history] == [identities(kind) for kind in ('Parameters', 'Layers', 'History')])
    ui.check('parameter scroll offset is preserved', abs(ui.call('get_scroll', view['id'])['result']['position'] - offset) < .1)
    for unused in range(3):
        ui.click('逐层')
        ui.check('layer mode presents one grid and hides the 3D pointer', len(ui.nodes('LayerCanvas')) == 1 and
                 not any(n['props'].get('onDown') for n in ui.nodes('Button', ui.nodes('Scene')[0])))
        ui.click('三维')
    ui.check('the layer grid is reused rather than remounted', canvas == identities('LayerCanvas'))
    ui.check('both preview buffers retain identity', models == [n['id'] for n in ui.nodes('PaperDoll')])
    before = next(s for s in ui.labels() if s.startswith('方块 '))
    ui.click('逐层')
    cells = ui.nodes('Button', ui.nodes('LayerCanvas')[0])
    ui.call('click', cells[0]['id']); time.sleep(.5)
    ui.click('历史')
    ui.check('a retained history pane receives the latest edit', any('绘制' in s for s in ui.labels()))
    ui.click('撤销'); ui.click('三维'); ui.click('参数')
    ui.check('undo from retained history restores the document', before in ui.labels())
    (ui.OUT / 'pane_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
