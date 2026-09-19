"""Native typography and persistent preview checks across actual scale changes."""
import json
import subprocess
import sys
import time
import verify_ui as ui
from verify_interaction import category
from simulate import _walk


def main():
    ui.click('工作台'); ui.click('浏览')
    category('cube'); ui.click('空心长方体')
    original = [n['id'] for n in ui.nodes('PaperDoll')]
    sizes = ('1280x720', '1600x900', '1440x1080', '1920x1080', '1366x768', '1920x1080')
    observed = []
    for size in sizes:
        process = subprocess.run([sys.executable, '-X', 'utf8', str(ui.ROOT /
            '.agents/skills/pyreact-debugging/scripts/resize_window.py'), '--size', size],
            capture_output=True, check=True, encoding='utf8')
        result = json.loads(process.stdout)
        assert result['ok'] and result['actualClient'] == result['requestedClient'], result
        time.sleep(.45)
        current = ui.tree()
        labels = ui.nodes('Label', current)
        sample = [n for n in labels if n['props'].get('content') in
                  ('现代化投影', '工作台', '参数', '图层', '历史', '本地草稿', '保存配置', '选取', '浏览')]
        assert len(sample) >= 8
        for label in sample:
            native = ui.call('native_control', label['id'])['result']
            assert label['props'].get('rasterText') and native['text'] == '', (size, label, native)
        ui.check(size + ' atlas text never draws duplicate native glyphs', True)
        fallback = [n for n in labels if n['props'].get('content') and not n['props'].get('rasterText')]
        assert fallback
        for label in fallback[:3]:
            assert ui.call('native_control', label['id'])['result']['text'] == label['props']['content']
        ui.check(size + ' native fallback text remains readable', True)
        observed.append(sample[0]['props']['fontSize'])
        ui.check(size + ' preview controls retain identity', original == [n['id'] for n in ui.nodes('PaperDoll', current)])
        tiles = ui.nodes('PreviewTile', current)
        ui.check(size + ' each persistent tile retains its two buffers', bool(tiles) and
                 all(len(ui.nodes('PaperDoll', tile)) == 2 for tile in tiles))
        # The same height and vertical midpoint for status, Save, and Close.
        save = next(n for n in ui.nodes('Action', current) if n['props'].get('label') == '保存配置')
        close = next(n for n in ui.nodes('Action', current) if n['props'].get('glyph') == 'close')
        a, b = ui.nodes('Button', save)[0]['layout'], ui.nodes('Button', close)[0]['layout']
        badge = next(parents[-2]['layout'] for n, parents in _walk(current)
                     if n.get('props', {}).get('content') in ('本地草稿', '草稿已保存'))
        ui.check(size + ' header status and buttons align', all(abs(a['height'] - box['height']) < .001 and
                 abs(a['y'] - box['y']) < .001 for box in (b, badge)))
    ui.check('regression covers multiple font scales', len(set(observed)) > 1)
    (ui.OUT / 'resize_checks.json').write_text(json.dumps({'checks': ui.checks,
        'font_sizes': observed}, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
