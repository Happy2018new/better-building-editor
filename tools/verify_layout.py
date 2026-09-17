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
ui.click('工作台')
for preset in ('20:9', '4:3', '16:10', '16:9'):
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
(ui.OUT / 'layout_checks.json').write_text(json.dumps(results, indent=2), encoding='utf8')
