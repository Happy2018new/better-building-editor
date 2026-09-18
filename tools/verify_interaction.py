"""Repeatable viewport gestures, direct edits, controls and native mouse checks."""
import json
import time
import sys
import verify_ui as ui

sys.path.insert(0, str(ui.ROOT / 'behavior_pack/HelloScript'))
from projection.camera import OrbitCamera


def pointer():
    return ui.nodes('Pointer', ui.nodes('Scene')[0])[0]


def gesture(phase, x, y, node=None):
    return ui.call('pointer', (node or pointer())['id'], {'phase': phase, 'x': x, 'y': y})


def point(pos, yaw=0., pitch=90.):
    layout = pointer()['layout']
    width, height = layout['width'], layout['height']
    return OrbitCamera(yaw, pitch).project(pos, (24, 16, 24), width, height, min(width, height) * .72 / 24.)


def tap(x, y):
    node = pointer()
    gesture('down', x, y, node)
    gesture('up', x, y, node)
    time.sleep(.25)


def category(glyph):
    action = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == glyph
                  and n['props'].get('width') == 40 and n['props'].get('height') == 37)
    ui.call('click', ui.nodes('Button', action)[0]['id'])
    time.sleep(.25)


def verify_outline():
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id'])
    time.sleep(.8)
    ui.click('浏览')
    tap(*point((8.5, 11., 14.5), 35., 25.))
    raw = ui.call('dump_tree')['tree']
    edges = [n for n in ui.nodes('Image', ui.nodes('Scene', raw)[0]) if 'rotatePivot' in n.get('props', {})]
    box = pointer()['layout']
    camera = OrbitCamera(35., 25.)
    errors = []
    for index, edge in enumerate(edges):
        axis, corner = index // 4, index % 4
        other = [i for i in range(3) if i != axis]
        a = [8, 10, 14]
        a[other[0]] += corner // 2
        a[other[1]] += corner % 2
        b = list(a); b[axis] += 1
        rect = ui.call('native_control', edge['id'])['result']['rect']
        for expected, actual in zip((a, b), rect[:2]):
            x, y = camera.project(expected, (24, 16, 24), box['width'], box['height'], min(box['width'], box['height']) * .72 / 24.)
            errors.extend((abs(actual[0] - box['x'] - x), abs(actual[1] - box['y'] - y)))
    ui.check('all 12 native outline edges meet the projected voxel corners', len(edges) == 12 and max(errors) < .15)


def main():
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')
    ui.click('浏览')
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id'])
    ui.click('俯视'); time.sleep(.7)
    for pos in [(8, 10, 14), (20, 5, 3), (12, 0, 3)]:
        tap(*point((pos[0] + .5, pos[1] + 1., pos[2] + .5)))
        ui.check('top picking %s' % (pos,), 'X %d · Y %d · Z %d' % pos in ui.labels())
    ui.click('吸管')
    tap(*point((20.5, 6., 3.5)))
    ui.check('eyedropper gets visible leaves', any('minecraft:leaves' in x for x in ui.labels()))
    ui.click('放置')
    tap(*point((8.5, 11., 14.5)))
    ui.check('placement goes to adjacent face', 'X 8 · Y 11 · Z 14' in ui.labels())
    ui.click('擦除')
    tap(*point((8.5, 12., 14.5)))
    ui.check('erase removes one visible voxel', any('擦除单格 · 已修改 1 格' in x for x in ui.labels()))
    ui.click('历史')
    ui.check('direct actions create undo history', any('绘制单格' in x for x in ui.labels()))
    ui.click('撤销'); ui.click('撤销')
    ui.click('参数'); ui.click('浏览')
    ui.click('正视'); time.sleep(.7)
    tap(*point((8.5, 7.5, 19.), pitch=0.))
    ui.check('front picking hits nearest back wall', 'X 8 · Y 7 · Z 18' in ui.labels())
    ui.click('框选')
    ui.click('俯视'); time.sleep(.7)
    tap(*point((8.5, 11., 14.5)))
    tap(*point((9.5, 11., 15.5)))
    ui.check('two clicks define 3D cuboid', '选区 4' in ui.labels())
    ui.click('恢复全选区域')
    ui.click('擦除')
    before = [x for x in ui.labels() if x.startswith('方块 ')]
    node = pointer(); layout = node['layout']
    x, y = layout['width'] / 2., layout['height'] / 2.
    gesture('down', x, y, node)
    for i in range(1, 9):
        gesture('move', x + i * 2, y - i, node)
        time.sleep(.04)
    gesture('cancel', x + 16, y - 8, node)
    time.sleep(.3)
    ui.check('drag in erase mode never paints', before == [x for x in ui.labels() if x.startswith('方块 ')])
    ui.click('浏览')
    props = ui.nodes('PaperDoll')[0]['props']
    ui.check('drag changes both orbit axes', abs(props['initRotZ']) > 5 and props['initRotX'] < -2)
    ui.click('俯视'); time.sleep(.7)
    tap(*point((8.5, 11., 14.5)))
    ui.check('preset after drag remains accurate', 'X 8 · Y 10 · Z 14' in ui.labels())
    category('cube'); ui.click('空心长方体')
    sliders = ui.nodes('Slider')
    ui.check('shell has only thickness slider', len(sliders) == 1)
    ui.call('scroll', ui.nodes('ScrollView')[-1]['id'], 10000)
    for value, label in [(0., '1 格'), (1., '8 格'), (.5, '5 格')]:
        ui.call('set_slider', ui.nodes('Slider')[0]['id'], value); time.sleep(.3)
        ui.check('thickness endpoint %s' % value, label in ui.labels())
    scroll = ui.nodes('Scroll')[-1]
    rail = ui.nodes('Pointer', scroll)[0]
    gesture('down', 2, 1, rail); gesture('up', 2, 1, rail)
    position = ui.call('get_scroll', ui.nodes('ScrollView')[-1]['id'])['result']['position']
    ui.check('custom vertical track returns to top', abs(position) < 2)
    category('brush'); ui.click('填充方块')
    ui.check('fill hides unrelated numeric settings', not ui.nodes('Slider'))
    verify_outline()
    ui.save('interaction_verified')
    (ui.OUT / 'interaction_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
