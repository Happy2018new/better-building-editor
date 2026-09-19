"""Live regression through the supported Pyreact clipboard protocol; requires an open workspace."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _protocol import request
from simulate import _walk, _resolve_label
from check_native_dialogs import assert_clear

OUT = ROOT / '.runtime'
checks = []

# Keep the display producing frames during a live test. This is scoped to this
# Python process and does not change the user's system power configuration.
if sys.platform == 'win32':
    import ctypes
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000003)


def call(command, node=None, value=None):
    assert_clear()
    result = request(command, node_id=node, value=value, timeout=15)
    assert_clear()
    if result is None and command in ('dump_tree', 'ping'):
        result = request(command, node_id=node, value=value, timeout=15)
    elif result is None and command == 'click':
        # A UI tree replacement may consume the clipboard acknowledgement.
        # Never repeat a write: the next assertion verifies the resulting state.
        result = request('ping', timeout=5)
    if not result or result.get('error'):
        raise AssertionError(result or 'IPC timed out')
    if command in ('dump_tree', 'dump_subtree'):
        # The in-game debugger polls the clipboard. Leaving a multi-megabyte
        # tree reply there would make every idle frame copy that entire reply
        # and distort native performance tests. Keep the parsed reply locally.
        acknowledgement = request('ping', timeout=5)
        assert acknowledgement and not acknowledgement.get('error'), acknowledgement
    return result


def tree():
    def visible(node):
        node['children'] = [visible(child) for child in node.get('children', [])
                            if child.get('style', {}).get('display') != 'none' and
                            child.get('style', {}).get('visible') is not False]
        return node
    return visible(call('dump_tree')['tree'])


def nodes(kind, root=None):
    return [n for n, unused in _walk(root or tree()) if n.get('type') == kind]


def labels(root=None):
    return [n['props'].get('content', '') for n in nodes('Label', root)]


def check(name, condition):
    checks.append({'name': name, 'passed': bool(condition)})
    print(('PASS ' if condition else 'FAIL ') + name, flush=True)
    assert condition, name


def click(text):
    matches = _resolve_label(tree(), text)
    exact = [n for n in matches if text in labels(n)]
    matches = exact or matches
    if len(matches) != 1:
        raise AssertionError('Ambiguous button %r: %s' % (text, [n['id'] for n in matches]))
    call('click', matches[0]['id'])
    time.sleep(.5)


def save(name):
    current = tree()
    (OUT / (name + '.json')).write_text(json.dumps({'tree': current}, ensure_ascii=False, indent=2), encoding='utf8')
    return current


def library_action(name, action):
    entries = [(node, parents) for node, parents in _walk(nodes('Library')[0])
               if node.get('type') == 'Label' and node.get('props', {}).get('content') == name]
    assert len(entries) == 1, (name, len(entries))
    for ancestor in reversed(entries[0][1]):
        targets = _resolve_label(ancestor, action)
        if len(targets) == 1:
            call('click', targets[0]['id'])
            time.sleep(.5)
            return
    raise AssertionError((name, action))


def new_region(size):
    """Use the three integer controls, without entering filtered text."""
    click('建筑库')
    for axis, value in enumerate(size):
        control = next(n for n in nodes('DimensionAxis') if n['props']['axis'] == axis)
        maximum = control['props']['maximum']
        assert 1 <= value <= maximum
        call('set_slider', nodes('Slider',control)[0]['id'], (value-1.)/(maximum-1.))
        time.sleep(.15)
    click('新建空白'); click('确认继续')


def main():
    click('建筑库')
    for unused in range(32):
        entries = [(n, parents) for n, parents in _walk(nodes('Library')[0]) if n.get('type') == 'Label' and
                   n.get('props', {}).get('content') == '自动验证 · 建筑样本']
        if not entries:
            break
        for ancestor in reversed(entries[0][1]):
            choices = _resolve_label(ancestor, '删除')
            if len(choices) == 1:
                call('click', choices[0]['id']); time.sleep(.4)
                click('确认继续')
                break
    click('工作台')
    from verify_selection_scope import diagnostic, wait_preview, click_point
    diagnostic({'fixture': 'offset_odd', 'selection': [[3, 1, 4], [3, 1, 4]]}); wait_preview()
    check('bounded pairs of persistent preview buffers created', 0 < len(nodes('PaperDoll')) <= 256 and len(nodes('PaperDoll')) % 2 == 0)
    before = diagnostic()['pose']
    click('右转')
    click('浏览')  # Publish the settled native camera pose into the UI snapshot.
    after = diagnostic()['pose']
    check('rotation updates rendered model', after != before)
    diagnostic({'layer': 1}); click('单层'); wait_preview(); click('俯视')
    check('single layer shares the editable 3D canvas', diagnostic()['displayMode'] == 'single' and len(nodes('Scene')) == 1)
    click('擦除'); click_point((3.5, 2., 4.5)); wait_preview()
    click('历史')
    check('single layer editing creates undo entry', diagnostic()['blocks'] == 71 and any('擦除' in s for s in labels()))
    click('撤销')
    check('undo creates redo action', any(n['props'].get('onClick') for n in _resolve_label(tree(), '重做')))
    click('参数')
    # Tool parameters are contextual; shell exposes the integer thickness range.
    from verify_interaction import category
    category('cube'); click('空心长方体')
    sliders = nodes('Slider')
    call('set_slider', sliders[0]['id'], .5); time.sleep(.5)
    check('slider feeds controlled state', .4 < nodes('Slider')[0]['props']['value'] < .7)
    scrolls = nodes('ScrollView')
    result = call('scroll', scrolls[-1]['id'], 100)
    check('inspector scroll accepts movement', result.get('error') is None)
    click('完整'); wait_preview()
    click('建筑库')
    entry = nodes('Input')[0]
    call('set_input', entry['id'], '自动验证 · 建筑样本'); time.sleep(.4)
    click('另存为新配置')
    check('library saves and displays a building', '自动验证 · 建筑样本' in labels())
    library_action('自动验证 · 建筑样本', '载入')
    check('load requires a confirmation dialog', '请确认这次操作' in labels())
    click('确认继续')
    check('load returns to workspace', '场景视图' in labels())
    click('入门指南')
    check('beginner guide renders six steps', '06' in labels())
    click('减少动态效果')
    save('ui_guide')
    click('减少动态效果')  # Restore the user's motion preference.
    click('投影')
    check('projection has controls and material counts', '所需材料' in labels())
    click('检查建造进度')
    for unused in range(20):
        current = labels()
        if any('已完成' in s or '尚未加载' in s for s in current):
            break
        time.sleep(.5)
    check('server responds to progress request', any('已完成' in s or '尚未加载' in s for s in labels()))
    click('更新 / 生成投影')
    check('transparent projection created', any('投影已生成' in s for s in labels()))
    click('关闭投影')
    check('projection can be removed', any('投影已关闭' in s for s in labels()))
    save('ui_projection')
    click('建筑库')
    library_action('自动验证 · 建筑样本', '删除'); click('确认继续')
    check('temporary configuration removed', '自动验证 · 建筑样本' not in labels(nodes('Library')[0]))
    click('工作台')
    save('ui_verified_workspace')
    (OUT / 'ui_checks.json').write_text(json.dumps(checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
