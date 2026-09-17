"""Live regression through the supported Pyreact clipboard protocol; requires an open workspace."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _protocol import request
from simulate import _walk, _resolve_label

OUT = ROOT / '.runtime'
checks = []


def call(command, node=None, value=None):
    result = request(command, node_id=node, value=value, timeout=15)
    if result is None and command in ('dump_tree', 'ping'):
        result = request(command, node_id=node, value=value, timeout=15)
    elif result is None and command == 'click':
        # A UI tree replacement may consume the clipboard acknowledgement.
        # Never repeat a write: the next assertion verifies the resulting state.
        result = request('ping', timeout=5)
    if not result or result.get('error'):
        raise AssertionError(result or 'IPC timed out')
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


def main():
    click('建筑库')
    for unused in range(32):
        entries = [(n, parents) for n, parents in _walk(tree()) if n.get('type') == 'Label' and
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
    check('preview created on first mount', len(nodes('PaperDoll')) == 1)
    before = tuple(nodes('PaperDoll')[0]['props'].get(k, 0) for k in ('initRotX', 'initRotY', 'initRotZ'))
    click('右转')
    after = tuple(nodes('PaperDoll')[0]['props'].get(k, 0) for k in ('initRotX', 'initRotY', 'initRotZ'))
    check('rotation updates rendered model', after != before)
    click('逐层')
    canvas = nodes('LayerCanvas')[0]
    cells = nodes('Button', canvas)
    check('layer canvas offers bounded interactive cells', len(cells) == 144)
    cell = cells[0]
    call('click', cell['id']); time.sleep(.5)
    click('历史')
    check('layer painting creates undo entry', any('绘制' in s for s in labels()))
    click('撤销')
    check('undo creates redo action', any(n['props'].get('onClick') for n in _resolve_label(tree(), '重做')))
    click('参数')
    sliders = nodes('Slider')
    call('set_slider', sliders[0]['id'], .5); time.sleep(.5)
    check('slider feeds controlled state', .4 < nodes('Slider')[0]['props']['value'] < .7)
    scrolls = nodes('ScrollView')
    result = call('scroll', scrolls[-1]['id'], 100)
    check('inspector scroll accepts movement', result.get('error') is None)
    click('三维')
    click('建筑库')
    entry = nodes('Input')[0]
    call('set_input', entry['id'], '自动验证 · 建筑样本'); time.sleep(.4)
    click('另存为新配置')
    check('library saves and displays a building', '自动验证 · 建筑样本' in labels())
    click('载入')
    check('load requires a confirmation dialog', '请确认这次操作' in labels())
    click('确认继续')
    check('load returns to workspace', '场景视图' in labels())
    click('入门指南')
    check('beginner guide renders six steps', '06' in labels())
    click('减少动态效果')
    save('ui_guide')
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
    click('删除'); click('确认继续')
    check('temporary configuration removed', '自动验证 · 建筑样本' not in labels(nodes('Library')[0]))
    click('工作台')
    save('ui_verified_workspace')
    (OUT / 'ui_checks.json').write_text(json.dumps(checks, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
