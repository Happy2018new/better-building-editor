"""Bounded touch callback simulation plus explicit confirmation in native UI."""
import json
import time
import verify_ui as ui
from verify_interaction import pointer
from verify_selection_scope import diagnostic, wait_preview, click_point
from verify_large_editor import snapshot
from projection.camera import OrbitCamera


def touch(pos, drag=False):
    state = diagnostic()
    node = pointer(); box = node['layout']
    camera = OrbitCamera(*state['pose']); camera.pan = tuple(state['pan'])
    x, y = camera.project(pos, state['sceneSize'], box['width'], box['height'],
                          min(box['width'], box['height']) * .72 * state['pose'][2] / max(state['sceneSize']))
    ui.call('pointer', node['id'], {'phase': 'down', 'x': x, 'y': y, 'touch': True})
    if drag:
        x += 20
        ui.call('pointer', node['id'], {'phase': 'move', 'x': x, 'y': y, 'touch': True})
    ui.call('pointer', node['id'], {'phase': 'leave', 'x': x, 'y': y, 'touch': True})
    ui.call('pointer', node['id'], {'phase': 'up', 'x': x, 'y': y, 'touch': True})
    time.sleep(.3)


def main():
    ui.click('工作台')
    diagnostic({'fixture': 'offset_odd', 'camera': [0, 90, 2], 'pan': [0, 0]})
    wait_preview(); ui.click('放置')
    before = diagnostic()
    touch((3.5, 4, 5.5))
    after = diagnostic()
    ui.check('touch auto enables explicit confirmation', after['touch'] and '确认放置' in ui.labels())
    ui.check('finger release retains proposed destination', after['placementTarget'] == [3, 4, 5])
    ui.check('tap does not mutate document or selection', all(before[k] == after[k] for k in ('blocks', 'selection', 'start', 'end')))
    snapshot('touch_placement_proposal')
    ui.click('确认放置'); wait_preview()
    ui.check('confirmation places exactly once', diagnostic()['blocks'] == 73 and diagnostic()['placementTarget'] is None)
    confirm = next(n for n in ui.nodes('Action') if n['props'].get('label') == '确认放置')
    ui.check('confirmation disables after committing', confirm['props'].get('enabled') is False)
    touch((4.5, 4, 6.5)); ui.click('取消')
    ui.check('cancel clears only proposal', diagnostic()['placementTarget'] is None and diagnostic()['blocks'] == 73)
    touch((4.5, 4, 6.5), True)
    ui.check('touch orbit never places or proposes', diagnostic()['placementTarget'] is None and diagnostic()['blocks'] == 73)
    diagnostic({'camera': [0, 90, 2]}); time.sleep(.8)
    touch((10.5, 0, 10.5))
    ui.check('touch can choose empty workplane', diagnostic()['placementTarget'] == [10, 0, 10])
    ui.click('擦除')
    ui.check('changing mode cancels touch placement', diagnostic()['placementTarget'] is None)
    ui.click('放置'); ui.click('触控放置')
    click_point((4.5, 4, 6.5)); wait_preview()
    ui.check('PC direct click remains supported', diagnostic()['blocks'] == 74 and not diagnostic()['touch'])
    (ui.OUT / 'touch_checks.json').write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
