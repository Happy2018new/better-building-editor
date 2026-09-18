"""Reversible live integration check in the development world (creative mode required)."""
import json
import time
import verify_ui as ui
from verify_interaction import category
from simulate import _walk


def wait_message(fragment):
    for unused in range(20):
        current = ui.labels()
        if any(fragment in text for text in current):
            return current
        if any('未写入' in text or '写入失败' in text for text in current):
            raise AssertionError(current[-8:])
        time.sleep(.4)
    raise AssertionError(current[-8:])


def main():
    ui.click('建筑库')
    inputs = ui.nodes('Input')
    ui.call('set_input', inputs[-1]['id'], '3, 3, 3'); time.sleep(.4)
    ui.click('新建空白'); ui.click('确认继续')
    ui.click('三维'); ui.click('浏览'); category('brush'); ui.click('填充方块')
    for node, ancestors in _walk(ui.tree()):
        if node.get('type') == 'Item' and node.get('props', {}).get('identifier') == 'minecraft:stone':
            button = next(parent for parent in reversed(ancestors) if parent['type'] == 'Button')
            ui.call('click', button['id']); time.sleep(.4)
            break
    ui.click('执行 · 填充方块')
    ui.check('27 block draft generated', '方块 27' in ui.labels())
    ui.click('投影')
    fields = ui.nodes('Input', ui.nodes('ProjectionSettings')[0])
    origin = [int(v.strip()) for v in fields[0]['props']['value'].split(',')]
    origin[1] += 30
    ui.call('set_input', fields[0]['id'], ', '.join(map(str, origin))); time.sleep(.4)
    ui.click('检查建造进度')
    current = wait_message('建造进度已更新')
    ui.check('test target is completely empty', '缺失 27 · 材质不符 0' in current)
    try:
        ui.click('应用到世界'); ui.click('确认继续')
        wait_message('已写入')
        ui.click('检查建造进度')
        current = wait_message('建造进度已更新')
        ui.check('server wrote all 27 blocks', '进度：27 / 27 已完成' in current)
    finally:
        ui.click('撤销世界写入'); ui.click('确认继续')
        wait_message('已撤销')
    ui.click('检查建造进度')
    current = wait_message('建造进度已更新')
    ui.check('world undo restores all 27 air cells', '缺失 27 · 材质不符 0' in current)
    (ui.OUT / 'world_checks.json').write_text(json.dumps(ui.checks, indent=2), encoding='utf8')
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')


if __name__ == '__main__':
    main()
