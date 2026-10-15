"""Navigation retention, search rebinding and live camera orientation checks."""
import json
import math
import time
import verify_ui as ui
import verify_interaction as interaction
from projection.camera import OrbitCamera
from simulate import _walk


def identities(kind):
    raw = ui.call('dump_tree')['tree']
    return [n['id'] for component in ui.nodes(kind, raw) for n, unused in _walk(component)
            if n.get('id', '').startswith('__pyr_')]


def axes():
    gizmo = ui.nodes('OrientationGizmo')[0]
    lines = [n for n in ui.nodes('Image', gizmo) if 'rotatePivot' in n.get('props', {})]
    return [ui.call('native_control', n['id'])['result'] for n in lines]


def verify_pose(yaw, pitch):
    gizmo = ui.nodes('Panel', ui.nodes('OrientationGizmo')[0])[0]['layout']
    scale = gizmo['width'] / 60.
    right, up, unused = OrbitCamera(yaw, pitch).basis()
    errors = []
    for axis, data in enumerate(axes()):
        if math.hypot(right[axis], up[axis]) < .02:
            ui.check('foreshortened axis is hidden', not data['visible'])
            continue
        origin = (gizmo['x'] + 30 * scale, gizmo['y'] + 30 * scale)
        tip = (origin[0] + 18 * scale * right[axis], origin[1] - 18 * scale * up[axis])
        for expected, actual in zip((origin, tip), data['rect'][:2]):
            errors.extend(abs(a - b) for a, b in zip(expected, actual))
    ui.check('native XYZ agrees with camera at %s / %s' % (yaw, pitch), max(errors) < .15)


def main():
    ui.click('工作台'); ui.click('三维'); ui.click('浏览'); ui.click('参数')
    model_ids = identities('PaperDoll')
    library_ids = identities('Library')
    groups = identities('ToolGroup')
    for glyph, expected in [('cube', '实心长方体'), ('brush', '填充方块'), ('cursor', '全选'),
                            ('move', '水平旋转'), ('grid', '棋盘拼色'), ('spark', '掏空内部')]:
        interaction.category(glyph)
        ui.check('category reveals correct tools: ' + glyph, any(expected in x for x in ui.labels(ui.nodes('ToolList')[0])))
    ui.check('category switches keep every native tool group', groups == identities('ToolGroup'))
    search = ui.nodes('Input', ui.nodes('ToolList')[0])[0]
    ui.call('set_input', search['id'], '空心长方体'); time.sleep(.4)
    ui.click('空心长方体')
    ui.check('search results execute current tool callbacks', bool(ui.nodes('Slider')))
    interaction.category('brush')
    ui.check('category resets search and restores its controls', ui.nodes('Input', ui.nodes('ToolList')[0])[0]['props']['value'] == '')
    for page, component in [('建筑库', 'Library'), ('入门指南', 'Guide'), ('投影', 'Viewport'), ('工作台', 'ToolList')]:
        ui.click(page)
        ui.check('page visibility: ' + page, len(ui.nodes(component)) == 1)
    ui.check('library controls survive page navigation', library_ids == identities('Library'))
    ui.check('model renderers survive all pages', model_ids == identities('PaperDoll'))
    ui.click('建筑库'); interaction.category('cube')
    ui.check('category from another page returns to the workspace', len(ui.nodes('ToolList')) == 1)
    ui.click('俯视'); time.sleep(.7); verify_pose(0., 90.)
    ui.click('正视'); time.sleep(.7); verify_pose(0., 0.)
    ui.click('右转'); time.sleep(.7); verify_pose(30., 0.)
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id']); time.sleep(.8)
    verify_pose(35., 25.)
    before = axes()
    pointer = interaction.pointer()
    x, y = pointer['layout']['width'] / 2., pointer['layout']['height'] / 2.
    interaction.gesture('down', x, y, pointer)
    interaction.gesture('move', x + 28, y - 10, pointer); time.sleep(.05)
    interaction.gesture('up', x + 28, y - 10, pointer); time.sleep(.5)
    ui.check('drag and inertia rotate the axes without a UI refresh', before != axes())
    ui.click('逐层'); ui.check('orientation widget is hidden in layer mode', not ui.nodes('OrientationGizmo'))
    ui.click('三维')
    ui.click('展开视图'); ui.check('orientation widget survives focused view', len(ui.nodes('OrientationGizmo')) == 1)
    ui.click('还原视图')
    (ui.OUT / 'navigation_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
