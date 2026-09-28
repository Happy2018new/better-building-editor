"""Check footer messages and native glyph layout in an instance-bound game."""
import json
import subprocess
import sys
import time

import verify_ui as ui
import capture_screen as capture
from verify_materials_paste import game as execute
from native_input_mode import open_workspace


def game(source):
    return execute(source.encode('ascii', 'backslashreplace').decode('ascii'))


def caption(kind):
    return ui.nodes('Label', ui.nodes(kind)[0])[0]


def ink(node):
    return game('''from modern_projection.pyreact import host, debug
from modern_projection.projection.typography import layout
h = host._ACTIVE_HOST[0]
f = debug.find_fiber_by_id(h._root_fiber, %r)
p = f.primitive_state
count = p.get('glyph_visible', 0)
_result = {'visible': count, 'pool': [id(c) for c in p['glyph_pool']],
           'rect': list(p['_layout_applied'][:2]),
           'native': h.GetBaseUIControl(f.native_path).GetSize(),
           'width': max(layout(f.props['content'], f.props['fontSize'])[1]),
           'patches': [(c.GetPosition(), c.GetSize()) for c in p['glyph_pool'][:count]]}
''' % node['id'])


def status(expected=None):
    node = caption('TaskStatus')
    content = node['props']['content']
    native = ink(node)
    assert content.strip() and native['visible'] > 0, (content, native)
    assert native['native'][0] > 30 and native['native'][1] > 0, native
    if expected is not None:
        assert content == expected, (content, expected)
    return node


def statistics():
    group = ui.nodes('DocumentStatistics')[0]
    labels = ui.nodes('Label', group)
    assert len(labels) == 3
    rectangles = [ui.call('native_control', n['id'])['result'] for n in labels]
    scale = labels[0]['props']['fontSize'] / 10.
    for node, rectangle in zip(labels, rectangles):
        native = ink(node)
        assert native['visible'] == len(node['props']['content']), (node, native)
        assert native['width'] <= rectangle['size'][0] + .02, (node, native)
        assert abs(rectangle['size'][0] - native['width'] - scale) < .1
    gaps = [b['global'][0] - a['global'][0] - a['size'][0]
            for a, b in zip(rectangles, rectangles[1:])]
    assert all(abs(gap - 12 * scale) < .1 for gap in gaps), gaps
    outer = ui.call('native_control', group['children'][0]['id'])['result']
    right = rectangles[-1]['global'][0] + rectangles[-1]['size'][0]
    assert abs(right - outer['global'][0] - outer['size'][0]) < .1
    left = ui.call('native_control', status()['id'])['result']
    assert left['global'][0] + left['size'][0] < rectangles[0]['global'][0]
    return [n['props']['content'] for n in labels]


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window, 'Bound game window is missing'
    capture._activate_window(window['hwnd'])
    original = capture._window_rect(window['hwnd'])
    open_workspace()
    time.sleep(1.)
    game('''assert not s.busy and s.io_job is None and s.edit_job is None
assert s.world_import_document is None
s._footer_saved = (s.editor.message, s.library, s.library_serial,
                   s.bridge.save_library, s.bridge.save_archive_page)
_result = True''')
    try:
        original_stats = statistics()
        original_pool = ink(caption('TaskStatus'))['pool']
        for field in ('point_edit', 'edit_progress', 'biome', 'library'):
            expected = '状态更新 ' + field
            game('s.editor.message = %r\ns.emit(%r)\n_result = True' % (expected, field))
            time.sleep(.12)
            status(expected)
            ui.check(field + ' updates visible footer ink', True)
        for mode in ('idle', 'world', 'edit', 'io'):
            for value in ('', ' \t\r\n', None):
                game('''s.editor.message = %r
s.busy = %r
s.edit_job = object() if %r else None
s.io_job = object() if %r else None
s.emit('edit_progress')
_result = True''' % (value, mode == 'world', mode == 'edit', mode == 'io'))
                time.sleep(.1)
                node = status()
                assert ink(node)['pool'] == original_pool
            ui.check(mode + ' empty/whitespace/None always shows text without cloning', True)
        game('''s.busy = False
s.io_job = s.edit_job = None
s.editor.message = '保存失败，请重试'
s.emit('library')
_result = True''')
        time.sleep(.15)
        status('保存失败，请重试')
        ui.check('nonempty errors retain their message', True)
        # Run the real archive completion; storage is replaced only in memory.
        game('''from modern_projection.projection.model import Document
s.library = []
s.bridge.save_library = lambda data: True
s.bridge.save_archive_page = lambda identity, part, value: True
s.import_world_capture(Document((1, 1, 1), {(0, 0, 0): ('minecraft:grass', 0)}), (1, 64, 2))
_result = True''')
        for unused in range(50):
            if game('_result = s.io_job is None'):
                break
            time.sleep(.1)
        assert game('_result = s.world_import_document is None and len(s.library) == 1')
        status('世界选区已导入建筑库')
        assert statistics() == original_stats
        ui.check('world import completion keeps draft statistics and displays success', True)
        resize = ui.ROOT / '.agents/skills/pyreact-debugging/scripts/resize_window.py'
        for size in ('1440x1080', '1920x1080', '2400x1080'):
            subprocess.run([sys.executable, str(resize), '--size', size, '--no-activate'],
                           check=True, capture_output=True)
            time.sleep(.6)
            statistics()
            # Check capacity for zero and upper-bound counts using live font
            # metrics; do not allocate a huge draft just to measure its caption.
            nodes = ui.nodes('Label', ui.nodes('DocumentStatistics')[0])
            for values in (('方块 0', '选区 0', '材质 0'),
                           ('方块 524,288', '选区 524,288', '材质 524288')):
                game('''from modern_projection.pyreact import host, debug
from modern_projection.projection.typography import layout
h = host._ACTIVE_HOST[0]
widths = []
for identity, value in %r:
    f = debug.find_fiber_by_id(h._root_fiber, identity)
    font = f.props['fontSize']
    available = max(layout(value, font)[1]) + font / 10.
    assert len(value) <= f.props['glyphSlots']
    widths.append(available)
assert sum(widths) + 24 * font / 10. <= 265 * font / 10.
_result = True''' % list(zip([n['id'] for n in nodes], values)))
            ui.check(size + ' counts fit, equal gaps, right edge aligned, status visible', True)
        # Keep an actual native capture for visual verification at 16:9.
        subprocess.run([sys.executable, str(resize), '--size', '1920x1080', '--no-activate'],
                       check=True, capture_output=True)
        time.sleep(.5)
        left, top, width, height = capture._window_rect(window['hwnd'])
        capture._capture_window_windows(window['hwnd'], width, height, False,
                                        str(ui.OUT / 'footer_fixed.png'))
    finally:
        game('''s.busy = False
s.edit_job = s.io_job = None
s.world_import_document = s.world_import_origin = None
s.editor.message, s.library, s.library_serial, s.bridge.save_library, s.bridge.save_archive_page = s._footer_saved
del s._footer_saved
s.emit()
_result = True''')
        subprocess.run([sys.executable, str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                        '--size', '%dx%d' % original[2:], '--no-activate'], check=True, capture_output=True)
        (ui.OUT / 'footer_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
