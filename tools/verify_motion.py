"""Measure actual native intermediate positions, presence, and rapid reversal."""
import json
import time
import verify_ui as ui
from simulate import _resolve_label
from clipboard_ipc import read_clipboard, write_clipboard


def fast(command, node_id):
    # The standard CLI deliberately sleeps 150 ms per request, too long to sample
    # a 250 ms animation. Keep the same seq protocol with a short local poll.
    seq = time.monotonic_ns()
    write_clipboard(json.dumps({'pyreact_debug': {'cmd': command, 'id': node_id, 'seq': seq}}))
    until = time.monotonic() + 5
    while time.monotonic() < until:
        time.sleep(.003)
        raw = read_clipboard()
        if not raw:
            continue
        try:
            value = json.loads(raw)
        except ValueError:
            continue
        if 'pyreact_ack' in value and value.get('seq') == seq:
            assert not value.get('error'), value
            return value
    raise AssertionError('Animation probe timed out')


def press(label):
    current = ui.tree()
    matches = [n for n in _resolve_label(current, label) if label in ui.labels(n)]
    assert len(matches) == 1
    fast('click', matches[0]['id'])


def check_segments():
    """The animated ink must be centered on the actual selected hit target."""
    current = ui.tree()
    for segment in ui.nodes('Segments', current):
        items = segment['props']['items']
        index = next((i for i, pair in enumerate(items) if pair[0] == segment['props'].get('value')), 0)
        rail = ui.nodes('Panel', segment)[0]
        highlight = ui.nodes('Panel', ui.nodes('Animated', segment)[0])[0]
        button = ui.nodes('Button', segment)[index]
        r, h, b = [ui.call('native_control', node['id'])['result'] for node in (rail, highlight, button)]
        label = items[index][1]
        ui.check(label + ' highlight is centered on its hit target', all(
            abs(h['global'][axis] + h['size'][axis] / 2. - b['global'][axis] - b['size'][axis] / 2.) < .01
            for axis in (0, 1)))
        top = h['global'][1] - r['global'][1]
        bottom = r['global'][1] + r['size'][1] - h['global'][1] - h['size'][1]
        ui.check(label + ' highlight has equal positive vertical insets', top > 0 and abs(top - bottom) < .01)


def main():
    if '取消' in ui.labels():
        ui.click('取消')
    ui.click('入门指南')
    reduced = next(n for n in ui.nodes('Action') if n['props'].get('label') == '减少动态效果')['props'].get('selected', False)
    if reduced:
        ui.click('减少动态效果')
    ui.click('工作台'); ui.click('浏览')
    ui.click('历史')
    check_segments()
    ui.click('参数')
    segments = next(n for n in ui.nodes('Segments') if ['select', '选取'] in n['props'].get('items', []))
    highlight = ui.nodes('Panel', ui.nodes('Animated', segments)[0])[0]['id']
    start = ui.call('native_control', highlight)['result']['position'][0]
    press('放置')
    positions = []
    for unused in range(9):
        positions.append(fast('native_control', highlight)['result']['position'][0])
        time.sleep(.016)
    time.sleep(.35)
    end = ui.call('native_control', highlight)['result']['position'][0]
    print('Selection positions:', start, positions, end, flush=True)
    ui.check('selection background traverses intermediate native positions',
             end > start and any(start + .1 < x < end - .1 for x in positions))
    press('框选'); time.sleep(.035); press('浏览')
    deadline = time.monotonic() + 2.
    while True:
        final = ui.call('native_control', highlight)['result']['position'][0]
        if abs(final - start) < .01 or time.monotonic() >= deadline:
            break
        time.sleep(.04)
    ui.check('rapid reversal ends on the requested option', abs(final - start) < .01)

    press('读取选区')
    samples = []
    for unused in range(7):
        confirm = ui.nodes('Confirmation', fast('dump_tree', None)['tree'])[0]
        cards = [n for n in ui.nodes('Panel', confirm) if n.get('style', {}).get('transform')]
        if cards:
            samples.append(cards[0]['style'].get('opacity'))
        time.sleep(.016)
    ui.check('dialog entrance contains intermediate opacity frames', any(0 < v < 1 for v in samples))
    time.sleep(.35)
    press('取消')
    closing = ui.nodes('Confirmation', fast('dump_tree', None)['tree'])[0]
    ui.check('dialog remains mounted during its exit', bool(ui.nodes('Image', closing)))
    time.sleep(.35)
    ui.check('dialog unmounts after exit', '请确认这次操作' not in ui.labels())
    ui.check('cancel preserves the editable viewport', 0 < len(ui.nodes('PaperDoll')) <= 256 and len(ui.nodes('Scene')) == 1)
    (ui.OUT / 'motion_checks.json').write_text(json.dumps({'checks': ui.checks,
        'selection_positions': positions, 'start': start, 'end': end,
        'dialog_opacity': samples}, ensure_ascii=False, indent=2), encoding='utf8')
    if reduced:
        ui.click('入门指南'); ui.click('减少动态效果'); ui.click('工作台')


if __name__ == '__main__':
    main()
