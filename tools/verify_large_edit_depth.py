"""Maximum-volume erase/undo and camera distance without geometry updates."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_large_editor import wait_for


def main():
    ui.click('工作台'); ui.click('浏览')
    started = time.perf_counter()
    diagnostic({'fixture': 'solid', 'camera': [0, 0, 1]})
    state, unused = wait_preview()
    initial_seconds = time.perf_counter() - started
    ui.check('maximum structure retains every block and exact preview dimensions',
             state['blocks'] == 409600 and state['sceneSize'] == [64, 100, 64] and state['sceneScale'] == 1)
    ui.click('擦除')
    ui.check('maximum cuboid selects region erase', diagnostic()['eraseScope'] == 'selection')
    ui.click('擦除选区'); wait_for('方块 0'); wait_preview()
    ui.check('whole-volume erase clears blocks and preserves selection',
             diagnostic()['blocks'] == 0 and diagnostic()['selection'] == 409600)
    ui.click('历史'); ui.click('撤销'); wait_for('方块 409,600'); wait_preview(); ui.click('参数')
    ui.check('single undo restores the entire maximum volume', diagnostic()['blocks'] == 409600)
    ui.click('浏览')
    started = time.perf_counter()
    before = diagnostic()
    ui.click('前移'); state, unused = wait_preview()
    depth_seconds = time.perf_counter() - started
    ui.check('forward distance keeps native dimensions and reuses all geometry',
             state['pose'][2] > 1.19 and state['blocks'] == 409600 and state['sceneSize'] == [64, 100, 64]
             and state['previewBuilds'] == before['previewBuilds'])
    click_point((32.5, 50.5, 64.))
    ui.check('maximum preview still picks the intact front wall', diagnostic()['focused'] == [32, 50, 63])
    report = {'initialPreviewSeconds': initial_seconds, 'depthPreviewSeconds': depth_seconds, 'checks': ui.checks}
    (ui.OUT / 'large_edit_depth_checks.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
