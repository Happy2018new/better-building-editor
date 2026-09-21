"""Live maximum-size draft verification. Does not write blocks to the world."""
import json
import sys
import time
import mss
from PIL import Image
import verify_ui as ui
from verify_interaction import category, pointer, gesture
import capture_screen as capture

NAME = '自动验证 · 大范围建筑'


def wait_for(fragment, timeout=60):
    started = time.perf_counter()
    while time.perf_counter() - started < timeout:
        labels = ui.labels()
        if any(fragment in value for value in labels):
            return time.perf_counter() - started
        time.sleep(.2)
    raise AssertionError((fragment, labels[-12:]))


def main():
    from verify_selection_scope import wait_preview
    capture.user32.SetProcessDPIAware()
    ui.new_region((64,100,64))
    ui.check('maximum draft selection is compact and interactive', '选区 409,600' in ui.labels())
    category('brush'); ui.click('填充方块')
    started = time.perf_counter()
    ui.click('执行：填充方块')
    wait_for('填充方块，已修改 409600 格')
    elapsed = time.perf_counter() - started
    ui.check('all 409,600 cells filled in game', '方块 409,600' in ui.labels())
    wait_preview()
    from verify_selection_scope import diagnostic
    ui.check('overview has native geometry', bool(diagnostic()['model']) and bool(ui.nodes('PaperDoll')))
    snapshot('large_overview')
    ui.click('历史'); ui.click('撤销'); wait_for('方块 0')
    ui.check('maximum fill undo works', '方块 0' in ui.labels())
    ui.click('重做'); wait_for('方块 409,600')
    ui.check('maximum fill redo works', '方块 409,600' in ui.labels())
    ui.click('参数'); ui.click('精细'); time.sleep(3)
    ui.check('exact local preview is available', '总览' in ui.labels())
    coordinates = next(n for n in ui.nodes('Coordinates') if n['props'].get('label') == '精细视图中心  X, Y, Z')
    ui.call('set_input', ui.nodes('Input', coordinates)[0]['id'], '63, 99, 63')
    time.sleep(3)
    ui.check('far corner can be located precisely', 'X 63   Y 99   Z 63' in ui.labels())
    snapshot('large_detail')
    ui.click('擦除'); ui.click('单格'); ui.click('俯视'); time.sleep(.7)
    node = pointer(); layout = node['layout']
    x, y = layout['width'] / 2., layout['height'] / 2.
    gesture('down', x, y, node); gesture('up', x, y, node)
    wait_for('方块 409,599')
    ui.check('direct picking edits one cell in large draft', '方块 409,599' in ui.labels())
    ui.click('历史'); ui.click('撤销'); wait_for('方块 409,600'); ui.click('参数')
    ui.click('总览'); ui.click('浏览')
    ui.click('图层')
    ui.check('layer panel is paginated', len(ui.nodes('Layers')[0]['children']) < 40)
    ui.click('参数')
    category('grid'); ui.click('随机混合')
    ui.click('执行：随机混合')
    ui.click('取消编辑'); wait_for('操作已取消')
    ui.check('cancelling a full-region procedural edit keeps draft intact', '方块 409,600' in ui.labels())
    ui.click('建筑库')
    field = ui.nodes('Input', ui.nodes('Library')[0])[0]
    ui.call('set_input', field['id'], NAME); time.sleep(.2)
    ui.click('另存为新配置'); wait_for('建筑已保存到本机建筑库')
    ui.check('maximum-size building saved', NAME in ui.labels())
    ui.library_action(NAME, '载入'); ui.click('确认继续')
    wait_for('已载入建筑配置')
    ui.check('maximum-size saved building restored', '方块 409,600' in ui.labels())
    ui.click('投影'); ui.click('更新 / 生成投影')
    wait_for('随玩家位置加载附近方块'); time.sleep(4)
    ui.click('关闭投影'); wait_for('投影已关闭')
    ui.check('large streamed projection starts and stops', True)
    ui.click('工作台')
    ui.save('large_editor_workspace')
    report = {'fillSecondsIncludingUI': elapsed, 'checks': ui.checks}
    (ui.OUT / 'large_editor_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if '--keep' in sys.argv:
        return
    ui.click('建筑库'); ui.library_action(NAME, '删除'); ui.click('确认继续')
    ui.click('入门指南'); ui.click('载入庭院示例'); ui.click('确认继续'); ui.click('工作台')


def snapshot(name):
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert capture._activate_window(window['hwnd'])
    time.sleep(.3)
    left, top, width, height = capture._window_rect(window['hwnd'])
    with mss.MSS() as screen:
        raw = screen.grab(dict(left=left, top=top, width=width, height=height))
        Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX').save(ui.OUT / (name + '.png'))


if __name__ == '__main__':
    main()
