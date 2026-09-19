"""Resize the real game and assert the three workspace columns stay inside its UI bounds."""
import json
import subprocess
import sys
import time
import verify_ui as ui
from simulate import _walk


def frame(node):
    return next(n['layout'] for n, unused in _walk(node) if n.get('layout'))


results = []
if '还原视图' in ui.labels():
    ui.click('还原视图')
ui.click('工作台')
from verify_selection_scope import diagnostic, wait_preview
diagnostic({'fixture': 'demo'}); wait_preview()
reset = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'home')
ui.call('click', ui.nodes('Button', reset)[0]['id'])
for preset in (sys.argv[1:] or ('20:9', '4:3', '16:10', '16:9')):
    process = subprocess.run([sys.executable, str(ui.ROOT / '.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                              '--preset', preset], capture_output=True, check=True, encoding='utf8')
    result = json.loads(process.stdout)
    assert result['ok'] and result['actualClient'] == result['requestedClient'], result
    time.sleep(.8)
    tree = ui.save('ui_layout_' + preset.replace(':', '_'))
    root = frame(tree)
    width, height = root['width'], root['height']
    ui.check(preset + ' screen ratio updated', abs(width / height - result['actualClient'][0] / result['actualClient'][1]) < .01)
    columns = {}
    for component in ('ToolList', 'Viewport', 'Inspector'):
        box = frame(ui.nodes(component, tree)[0])
        columns[component] = box
        ui.check(preset + ' ' + component + ' fits', box['width'] > 0 and box['height'] > 0 and
                 box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= width + .5 and
                 box['y'] + box['height'] <= height + .5)
    results.append({'preset': preset, 'client': result['actualClient'], 'ui': root, 'columns': columns})
    viewport = columns['Viewport']
    actions = ui.nodes('Action', ui.nodes('Viewport', tree)[0])
    ui.check(preset + ' icon toolbars stay inside the viewport', all(
        frame(action)['x'] >= viewport['x'] - .5 and
        frame(action)['x'] + frame(action)['width'] <= viewport['x'] + viewport['width'] + .5
        for action in actions))
    tools = ui.nodes('Action', ui.nodes('ToolList', tree)[0])
    ui.check(preset + ' visible tool entries have icons and aligned labels', bool(tools) and all(
        action['props'].get('glyph') and action['props'].get('leading') for action in tools))
    # Hit coordinates must continue to agree with the fitted native model after resize.
    import verify_interaction as interaction
    ui.click('浏览'); ui.click('俯视'); time.sleep(.6)
    interaction.tap(*interaction.point((8.5, 11., 14.5)))
    ui.check(preset + ' resized viewport picks roof', 'X 8 · Y 10 · Z 14' in ui.labels())
    canvas = ui.nodes('Scene')[0]['children'][0]
    clip = next(child for child in canvas['children'] if ui.nodes('PaperDoll', child))
    native_clip = ui.call('native_control', clip['id'])['result']
    ui.check(preset + ' native scissor has integral boundaries',
             all(abs(v - round(v)) < .001 for v in native_clip['global'] + native_clip['size']))
    native_canvas = ui.call('native_control', canvas['id'])['result']
    # The unused buffer can have no model and a zero-size hidden parent. Check
    # the displayed renderer, whose parent owns native visibility.
    surfaces = [n for n in ui.nodes('Panel', clip) if n['id'].startswith('surface')]
    visible_surface = next(n for n in surfaces if ui.call('native_control', n['id'])['result']['visible'])
    native_model = ui.call('native_control', ui.nodes('PaperDoll', visible_surface)[0]['id'])['result']
    ui.check(preset + ' clip snapping preserves the model origin',
             all(abs(a - (b-p)) < .001 for a, b, p in zip(native_canvas['global'], native_model['global'], native_model['position'])))
    before = interaction.pointer()
    ui.click('展开视图')
    expanded = interaction.pointer()
    ui.check(preset + ' focus enlarges viewport and retains native input', expanded['id'] == before['id'] and
             expanded['layout']['width'] > before['layout']['width'] * 1.5 and
             expanded['layout']['height'] > before['layout']['height'] * 1.15)
    ui.check(preset + ' focus collapses tool panels', not ui.nodes('ToolList') and not ui.nodes('Inspector'))
    interaction.tap(*interaction.point((8.5, 11., 14.5)))
    ui.check(preset + ' focus viewport still picks roof', 'X 8 · Y 10 · Z 14' in ui.labels())
    ui.click('材质与属性')
    ui.check(preset + ' focus inspector fits', frame(ui.nodes('Inspector')[0])['x'] +
             frame(ui.nodes('Inspector')[0])['width'] <= width + .5)
    interaction.tap(*interaction.point((8.5, 11., 14.5)))
    ui.check(preset + ' docked focus viewport still picks roof', 'X 8 · Y 10 · Z 14' in ui.labels())
    ui.click('材质与属性'); ui.click('还原视图')
    restored = interaction.pointer()
    ui.check(preset + ' restore preserves native renderer and exact viewport size', restored['id'] == before['id'] and
             restored['layout'] == before['layout'])
(ui.OUT / 'layout_checks.json').write_text(json.dumps(results, indent=2), encoding='utf8')
