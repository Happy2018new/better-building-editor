"""Focused viewport must retain editing, undo, materials and renderer identity."""
import json
import time
import verify_ui as ui
import verify_interaction as interaction


def main():
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')
    ui.click('完整'); ui.click('俯视'); ui.click('放置')
    reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
    ui.call('click', ui.nodes('Button', reset)[0]['id']); ui.click('俯视'); time.sleep(.7)
    ids = [n['id'] for n in ui.nodes('PaperDoll')]
    initial = interaction.pointer()['layout']
    ui.click('展开视图')
    focused = interaction.pointer()['layout']
    ui.check('maximize retains all tile model buffers', [n['id'] for n in ui.nodes('PaperDoll')] == ids)
    interaction.tap(*interaction.point((8.5, 11., 14.5)))
    ui.check('place directly in maximized viewport', 'X 8 · Y 11 · Z 14' in ui.labels())
    undo = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'undo')
    ui.call('click', ui.nodes('Button', undo)[0]['id']); time.sleep(.6)
    ui.check('focused toolbar undo restores document', '方块 1,307' in ui.labels())
    ui.click('材质与属性')
    ui.check('focused materials are editable', len(ui.nodes('MaterialPicker')) == 1)
    ui.click('图层')
    ui.check('focused layers accessible', len(ui.nodes('Layers')) == 1)
    ui.click('历史')
    ui.check('focused history accessible', len(ui.nodes('History')) == 1)
    ui.click('材质与属性'); ui.click('单层')
    ui.check('focused single layer uses the same 3D scene', len(ui.nodes('Scene')) == 1 and not ui.nodes('LayerCanvas'))
    ui.click('完整'); ui.click('还原视图')
    ui.check('restore retains model buffers and layout', [n['id'] for n in ui.nodes('PaperDoll')] == ids and
             interaction.pointer()['layout'] == initial)
    result = dict(checks=ui.checks, normal=initial, focus=focused,
                  area_ratio=focused['width'] * focused['height'] / (initial['width'] * initial['height']))
    (ui.OUT / 'focus_checks.json').write_text(json.dumps(result, indent=2), encoding='utf8')
    print('Focused viewport area multiplier: %.2f' % result['area_ratio'])


if __name__ == '__main__':
    main()
