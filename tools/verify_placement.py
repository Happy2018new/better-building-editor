"""Live regression for selection/mode changes, ceiling placement and model lifetime."""
import json
import time
import verify_ui as ui
import verify_interaction as interaction
from verify_selection_scope import diagnostic


def main():
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')
    ui.click('三维'); ui.click('俯视'); time.sleep(.7)
    raw = ui.call('dump_tree')['tree']
    renderer_ids = [n['id'] for n in ui.nodes('PaperDoll', raw)]
    x, y = interaction.point((8.5, 11., 14.5))
    for mode in ('选取', '框选', '换材质', '擦除', '吸管', '浏览'):
        ui.click(mode)
        if mode in ('选取', '框选'):
            interaction.tap(x, y)
            if mode == '框选':
                interaction.tap(x, y)
        ui.click('放置')
        interaction.tap(x, y)
        ui.check('placement works after ' + mode,
                 any('绘制单格 · 已修改 1 格' in label for label in ui.labels()))
        state = diagnostic()
        ui.check('one shared selection marks the destination cell after ' + mode,
                 state['selection'] == 1 and state['start'] == state['end'] == [8, 11, 14])
        # Real document undo through the inspector; then return to direct mode.
        ui.click('历史'); ui.click('撤销'); ui.click('参数')
    ui.check('direct edits retain one shared selection', '选区 1' in ui.labels())
    for height in range(11, 16):
        interaction.tap(x, y)
        ui.check('place at Y=%d' % height, 'X 8 · Y %d · Z 14' % height in ui.labels())
    interaction.tap(x, y)
    ui.check('ceiling is rejected without losing the preview',
             any('目标超出建筑范围' in label for label in ui.labels()))
    # Repeated model replacement, page changes and undo reuse both native surfaces.
    for index in range(12):
        ui.click('擦除'); interaction.tap(x, y)
        ui.click('放置'); interaction.tap(x, y)
        if index % 3 == 0:
            ui.click('建筑库'); ui.click('工作台')
        ui.check('replacement cycle %d completed' % (index + 1),
                 any('绘制单格 · 已修改 1 格' in label for label in ui.labels()))
    raw = ui.call('dump_tree')['tree']
    ui.check('both native renderers survive all edits and navigation',
             renderer_ids == [n['id'] for n in ui.nodes('PaperDoll', raw)])
    (ui.OUT / 'placement_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
