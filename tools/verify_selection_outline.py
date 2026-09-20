"""Persistent region outline across real hover, tool changes and touch input."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_interaction import pointer, category
from verify_global_cursor import hover, touch, screen_point
from verify_large_editor import snapshot
from mcdk import Client, return_value


def outline():
    raw = ui.call('dump_tree')['tree']
    edges = [n for n in ui.nodes('Image', ui.nodes('Scene', raw)[0])
             if 'rotatePivot' in n.get('props', {})][-12:]
    assert len(edges) == 12
    code = (
        'import json\n'
        'from HelloScript.pyreact import host, debug\n'
        '_result = json.dumps([debug.dispatch_editor_command('
        'host._ACTIVE_HOST[0], "native_control", identity, None) for identity in %r])\n'
    ) % [n['id'] for n in edges]
    ui.assert_clear()
    with Client(timeout=15) as client:
        result = return_value(client.call('execute_code', {
            'code': code, 'is_client': True, 'direct_return': True}))
    ui.assert_clear()
    return json.loads(result)


def same_outline(a, b):
    return all(x['visible'] == y['visible'] and x['rect'] == y['rect']
               for x, y in zip(a, b))


def click_voxel(pos):
    hover(pos)
    capture.user32.mouse_event(2, 0, 0, 0, 0)
    time.sleep(.055)
    capture.user32.mouse_event(4, 0, 0, 0, 0)
    time.sleep(.25)


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left, top, unused_width, unused_height = capture._window_rect(window['hwnd'])

    def leave():
        capture.user32.SetCursorPos(left + 30, top + 40)
        time.sleep(.2)

    leave()
    ui.click('工作台'); ui.click('完整')
    diagnostic({'fixture': 'interior', 'size': [8, 8, 8], 'camera': [0, 0, 1]})
    wait_preview(); ui.click('框选')
    click_voxel((2.5, 2.5, 8)); click_voxel((5.5, 5.5, 8))
    state = diagnostic()
    ui.check('two real clicks complete one region', state['selection'] == 16 and state['anchor'] is None)
    leave(); completed = outline()
    hover((3.5, 3.5, 8))
    ui.check('completed box survives hover in box mode', same_outline(completed, outline()))

    # Semantic toolbar clicks keep the real mouse stationary over the model.
    for mode in ('浏览', '选取', '放置', '换材质', '擦除', '吸管', '框选'):
        ui.click(mode)
        actual = outline()
        if not same_outline(completed, actual):
            (ui.OUT / 'selection_outline_failure.json').write_text(json.dumps(
                {'mode': mode, 'state': diagnostic(), 'expected': completed, 'actual': actual},
                ensure_ascii=False, indent=2), encoding='utf8')
            snapshot('selection_outline_failure')
        ui.check(mode + ' retains the region under a stationary pointer', same_outline(completed, actual))
        hover((4.5, 4.5, 8))
        ui.check(mode + ' retains the region when hover moves', same_outline(completed, outline()))
        ui.check(mode + ' does not mutate the shared selection', diagnostic()['selection'] == 16)
        hover((3.5, 3.5, 8))

    category('cube'); ui.click('空心长方体')
    ui.check('batch tool keeps its complete visible scope', same_outline(completed, outline()))
    ui.click('擦除'); ui.click('单格')
    ui.check('erase scope change keeps the region until an edit', same_outline(completed, outline()))
    ui.click('选区')
    click_voxel((3.5, 3.5, 8))
    ui.check('selection erase click preserves the region', diagnostic()['selection'] == 16 and same_outline(completed, outline()))
    snapshot('selection_outline_preserved')

    ui.click('框选'); click_voxel((1.5, 1.5, 8))
    first = outline()
    ui.check('new first corner immediately replaces the old region',
             diagnostic()['selection'] == 1 and diagnostic()['anchor'] == [1, 1, 7] and not same_outline(completed, first))
    hover((3.5, 3.5, 8))
    ui.check('unfinished box follows the next corner', not same_outline(first, outline()))
    click_voxel((3.5, 3.5, 8))
    leave(); next_region = outline(); hover((2.5, 2.5, 8))
    ui.check('new completed region stays visible', diagnostic()['selection'] == 9 and same_outline(next_region, outline()))

    leave(); ui.click('浏览')
    x, y = screen_point((2.5, 2.5, 8)); node = pointer()['id']
    ui.call('pointer', node, {'phase': 'down', 'x': x, 'y': y, 'touch': True})
    time.sleep(.1)
    ui.check('touch down does not replace a completed region', same_outline(next_region, outline()))
    ui.call('pointer', node, {'phase': 'cancel', 'touch': True})
    touch((4.5, 4.5, 8))
    ui.check('touch release still selects a single voxel', diagnostic()['selection'] == 1 and diagnostic()['focused'] == [4, 4, 7])

    # A successful placement ends the region; subsequent hover stays responsive.
    diagnostic({'fixture': 'offset_odd', 'selection': [[2, 1, 3], [5, 3, 8]], 'camera': [0, 90, 1]})
    wait_preview(); ui.click('放置')
    click_voxel((3.5, 4, 4.5)); wait_preview()
    ui.check('placement commits exactly one new cell', diagnostic()['selection'] == 1 and diagnostic()['blocks'] == 73)
    placed = outline(); hover((4.5, 4, 4.5))
    ui.check('single-cell placement preview still follows the mouse',
             diagnostic()['cursorCell'] == [4, 4, 4] and not same_outline(placed, outline()))
    leave()
    (ui.OUT / 'selection_outline_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
