"""Real mouse coverage for viewport navigation and selection boundary buttons."""
import json
import time
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_large_editor import snapshot
from mcdk import Client, return_value


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    left, top, physical_width, unused = capture._window_rect(window['hwnd'])
    capture.user32.SetCursorPos(left + 30, top + 40)
    ui.click('工作台'); ui.click('浏览'); ui.click('参数'); ui.click('完整')
    diagnostic({'fixture': 'demo', 'camera': [0, 0, 1]}); wait_preview()
    tree = ui.tree()
    root = ui.nodes('SafeArea', tree)[0]['children'][0]['layout']
    scale = physical_width / root['width']
    results = []

    def click_native(action):
        button = action if action.get('type') == 'Button' else ui.nodes('Button', action)[0]
        native = ui.call('native_control', button['id'])['result']
        x, y = native['global']; w, h = native['size']
        assert w > 0 and h > 0 and native['visible'], native
        assert capture.user32.GetForegroundWindow() == window['hwnd'], 'game lost foreground'
        capture.user32.SetCursorPos(int(left + (x + w / 2.) * scale), int(top + (y + h / 2.) * scale))
        time.sleep(.18)
        capture.user32.mouse_event(2, 0, 0, 0, 0)
        try:
            time.sleep(.1)
        finally:
            capture.user32.mouse_event(4, 0, 0, 0, 0)
        time.sleep(.6)
        return native

    def record(name, before, after, passed, native):
        results.append({'name': name, 'passed': passed, 'before': before, 'after': after, 'native': native})
        print(('PASS ' if passed else 'FAIL ') + name, flush=True)

    with Client() as client:
        names = return_value(client.call('execute_code', {'code': '''
from modern_projection.pyreact import host
def visit(fiber):
    result=[]
    if fiber.is_primitive:
        result.append((isinstance(fiber.native_name,str) and isinstance(fiber.native_path,str),fiber.key is not None))
    for child in fiber.child_fibers:result.extend(visit(child))
    return result
items=visit(host._ACTIVE_HOST[0]._root_fiber)
_result={'valid':all(item[0] for item in items),'keyed':sum(item[1] for item in items)}
''', 'is_client': True, 'direct_return': True}))
    record('all keyed controls use SDK byte-string names and paths', None, names, names['valid'] and names['keyed'] > 0, None)

    navigation = ui.nodes('Action', ui.nodes('ViewNavigation', tree)[0])
    for action, axis, delta in zip(navigation[:4], (0, 0, 1, 1), (.12, -.12, .12, -.12)):
        before = diagnostic(); native = click_native(action); after = diagnostic()
        expected = list(before['pan']); expected[axis] += delta
        record('native ' + action['props']['label'], before, after,
               all(abs(a-b) < .001 for a, b in zip(expected, after['pan'])), native)
    for label, sign in (('前移', 1), ('后移', -1)):
        action = next(n for n in ui.nodes('Action', ui.nodes('ViewNavigation')[0]) if n['props']['label'] == label)
        before = diagnostic(); native = click_native(action); after = diagnostic()
        record('native ' + label, before, after, (after['depthTarget'] - before['depthTarget']) * sign > 0, native)

    # These are ordinary native button clicks, not direct callback dispatch.
    for label, component in (('图层', 'Layers'), ('历史', 'History'), ('参数', 'Parameters')):
        target = ui._resolve_label(ui.tree(), label)
        target = [n for n in target if label in ui.labels(n)] or target
        assert len(target) == 1, (label, target)
        native = click_native(target[0])
        record('native inspector tab ' + label, None, None, len(ui.nodes(component)) == 1, native)

    def action_by_label(label):
        return next(n for n in ui.nodes('Action') if n['props'].get('label') == label)

    for visible in (True, False):
        native = click_native(action_by_label('坐标设置'))
        record('native coordinate toggle ' + str(visible), None, None,
               bool(ui.nodes('Coordinates', ui.nodes('Parameters')[0])) == visible, native)

    actions = ui.nodes('Action', ui.nodes('SelectionBounds')[0])
    assert len(actions) == 12
    for axis in range(3):
        for side, delta, offset in ((0, 1, 1), (0, -1, 0), (1, -1, 2), (1, 1, 3)):
            before = diagnostic(); native = click_native(actions[axis * 4 + offset]); after = diagnostic()
            field = 'start' if side == 0 else 'end'
            expected = list(before[field]); expected[axis] += delta
            record('native boundary %s %s %+d' % ('XYZ'[axis], field, delta), before, after,
                   after[field] == expected, native)
    for offset in (0, 3, 4, 7, 8, 11):
        before = diagnostic(); native = click_native(actions[offset]); after = diagnostic()
        record('disabled outer boundary %d stays unchanged' % offset, before, after,
               all(before[k] == after[k] for k in ('start', 'end', 'selection', 'blocks')), native)

    diagnostic({'selection': [[2, 2, 2], [4, 4, 4]]})
    native = click_native(action_by_label('全选')); state = diagnostic()
    record('native select all restores the document bounds', None, state,
           state['selection'] == 24*16*24 and state['start'] == [0,0,0] and state['end'] == [23,15,23], native)
    record('toolbar clicks never edit or rotate the model', None, state,
           state['blocks'] == 1307 and state['pointerStats'] == [0,0,0,0] and state['pose'] == [0.,0.,1.], None)
    snapshot('native_buttons_result')
    (ui.OUT / 'native_buttons_checks.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
    assert all(item['passed'] for item in results), 'native button regression; inspect native_buttons_checks.json'


if __name__ == '__main__':
    main()
