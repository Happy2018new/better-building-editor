"""Retained native panes must survive navigation and refresh after editing."""
import json
import time
import verify_ui as ui
from simulate import _walk
from verify_selection_scope import diagnostic, wait_preview, click_point


def identities(kind):
    # Include inactive panes: they remain mounted but cannot receive input.
    raw = ui.call('dump_tree')['tree']
    component = next(n for n, unused in _walk(raw) if n.get('type') == kind)
    return [n['id'] for n, unused in _walk(component) if n.get('id', '').startswith('__pyr_')]


def main():
    ui.click('工作台'); ui.click('完整'); ui.click('浏览'); ui.click('参数')
    diagnostic({'fixture': 'offset_odd', 'layer': 1, 'selection': [[3, 1, 4], [3, 1, 4]]}); wait_preview()
    params, layers, history = [identities(kind) for kind in ('Parameters', 'Layers', 'History')]
    scene = [n['id'] for n in ui.nodes('Scene')]
    models = [n['id'] for n in ui.nodes('PaperDoll')]
    view = ui.nodes('ScrollView', ui.nodes('Parameters')[0])[0]
    offset = ui.call('scroll', view['id'], 45)['result']['position']
    for label in ('图层', '历史', '参数', '历史', '图层', '参数'):
        ui.click(label)
    ui.check('all inspector controls are reused across repeated switches',
             [params, layers, history] == [identities(kind) for kind in ('Parameters', 'Layers', 'History')])
    ui.check('parameter scroll offset is preserved', abs(ui.call('get_scroll', view['id'])['result']['position'] - offset) < .1)
    for unused in range(3):
        ui.click('单层'); wait_preview()
        ui.check('single layer keeps the shared 3D scene editable', diagnostic()['displayMode'] == 'single' and
                 any(n['props'].get('onDown') for n in ui.nodes('Pointer', ui.nodes('Scene')[0])))
        ui.click('完整'); wait_preview()
    ui.check('the same scene survives display mode changes', scene == [n['id'] for n in ui.nodes('Scene')])
    ui.check('both preview buffers retain identity', models == [n['id'] for n in ui.nodes('PaperDoll')])
    before = next(s for s in ui.labels() if s.startswith('方块 '))
    ui.click('单层'); wait_preview(); ui.click('俯视'); ui.click('擦除')
    click_point((3.5, 2., 4.5)); wait_preview()
    ui.click('历史')
    ui.check('a retained history pane receives the latest edit', diagnostic()['blocks'] == 71 and any('擦除' in s for s in ui.labels()))
    ui.click('撤销'); ui.click('完整'); wait_preview(); ui.click('参数')
    ui.check('undo from retained history restores the document', before in ui.labels())
    (ui.OUT / 'pane_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
