"""All click modes, repeated box starts and native single-outline feedback."""
import json
import time
import verify_ui as ui
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_viewport_revision import outline_edges
from verify_large_editor import snapshot


def shared_cell(expected):
    state = diagnostic()
    ui.check('one selected cell at ' + str(expected),
             state['selection'] == 1 and state['start'] == state['end'] == expected)
    bounds = ui.nodes('SelectionBounds')[0]
    labels = ui.labels(bounds)
    ui.check('sidebar shows the same cell bounds', all(str(v) in labels for v in expected))
    edges = outline_edges()
    ui.check('only twelve visible edges mark the current cell', len(edges) == 12 and all(
        ui.call('native_control', edge['id'])['result']['visible'] for edge in edges))


def main():
    ui.click('工作台')
    diagnostic({'fixture': 'offset_odd', 'camera': [0, 90, 1]})
    wait_preview(); time.sleep(.5)
    for mode in ('浏览', '选取', '吸管', '换材质', '擦除', '放置'):
        diagnostic({'selection': [[2, 1, 3], [5, 3, 8]]})
        ui.click(mode)
        if mode == '擦除': ui.click('单格')
        click_point((3.5, 4, 5.5))
        wait_preview()
        # Erase removes Y3; placement restores and selects that destination.
        shared_cell([3, 3, 5])

    diagnostic({'selection': [[2, 1, 3], [5, 3, 8]]})
    ui.click('框选')
    for index in range(2):
        click_point((3.5, 4, 5.5))
        shared_cell([3, 3, 5])
        ui.check('box starts with a new anchor', diagnostic()['anchor'] == [3, 3, 5])
        click_point((5.5, 4, 8.5))
        state = diagnostic()
        ui.check('second click commits the exact cuboid', state['selection'] == 12 and state['anchor'] is None)
    click_point((3.5, 4, 5.5))
    ui.click('全选')
    state = diagnostic()
    ui.check('select all abandons unfinished two-point selection', state['anchor'] is None and state['selection'] == 23*15*21)
    ui.click('吸管'); click_point((3.5, 4, 5.5))
    shared_cell([3, 3, 5])
    snapshot('click_selection_unified')
    (ui.OUT / 'click_selection_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
