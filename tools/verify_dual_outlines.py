"""Real mouse/gradient pixels and F11 native touch outline regression."""
import json
import sys
import time
import mss
import numpy as np
from PIL import Image
import verify_ui as ui
import capture_screen as capture
from verify_selection_scope import diagnostic, wait_preview
from verify_selection_outline import outline, same_outline, click_voxel
from verify_global_cursor import hover
from verify_native_touch import touch
from native_input_mode import set_touch, state as input_state, key as native_key
from verify_large_editor import snapshot


def visible(lines):
    return any(line['visible'] for line in lines)


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    hwnd = window['hwnd']
    left, top, pixel_w, pixel_h = capture._window_rect(hwnd)

    def leave():
        capture.user32.SetCursorPos(left + 30, top + 40)
        time.sleep(.2)

    def key(code):
        assert capture.user32.GetForegroundWindow() == hwnd
        native_key(chr(code).lower())

    def close_open():
        action = next(n for n in ui.nodes('Action') if n['props'].get('glyph') == 'close')
        ui.call('click', ui.nodes('Button', action)[0]['id'])
        time.sleep(.6)
        key(80)
        time.sleep(1.)
        diagnostic.identity = None  # Closing the UI destroys the old Scene.

    if '--finish' in sys.argv:
        diagnostic({'fixture': 'interior', 'size': [8, 8, 8], 'camera': [0, 0, 1]})
        wait_preview()
        finish(window, close_open, leave)
        return
    leave()
    assert not diagnostic()['touch'], 'Start this check in native mouse mode.'
    # Do not send a model click before this first-entry regression.
    assert diagnostic()['pointerStats'] == [0, 0, 0, 0], 'Use a fresh instance for initial hover.'
    diagnostic({'fixture': 'interior', 'size': [8, 8, 8], 'camera': [0, 0, 1]})
    wait_preview(); ui.click('选取')
    initial = diagnostic(); selected = outline()
    hover((3.5, 3.5, 8))
    ui.check('first hover works without any model press', diagnostic()['cursorCell'] == [3, 3, 7] and
             diagnostic()['pointerStats'] == [0, 0, 0, 0] and visible(outline('cursor')))
    ui.check('first hover preserves the selected region', same_outline(selected, outline()) and
             diagnostic()['selection'] == initial['selection'])
    hover((5.5, 5.5, 8)); first_cursor = outline('cursor')
    ui.check('cursor moves before the first click', diagnostic()['cursorCell'] == [5, 5, 7] and visible(first_cursor))

    click_voxel((2.5, 2.5, 8)); single = outline()
    ui.check('clicked cell is selected immediately while mouse stays inside', diagnostic()['focused'] == [2, 2, 7] and
             diagnostic()['selection'] == 1 and visible(single) and not same_outline(single, selected))
    hover((5.5, 5.5, 8))
    ui.check('selected cell and moving cursor coexist', same_outline(single, outline()) and visible(outline('cursor')) and
             not same_outline(single, outline('cursor')))
    click_voxel((4.5, 4.5, 8)); next_single = outline()
    ui.check('next click updates blue cell without leaving the building', diagnostic()['focused'] == [4, 4, 7] and
             not same_outline(single, next_single))
    leave()
    ui.check('leaving hides only the cursor', not visible(outline('cursor')) and same_outline(next_single, outline()))

    ui.click('框选'); click_voxel((2.5, 2.5, 8))
    first_corner = outline('cursor')
    ui.check('first desktop corner has only one spectrum cube', not visible(outline()) and visible(first_corner))
    hover((5.5, 5.5, 8)); pending = outline('cursor')
    ui.check('pending desktop box replaces the small cursor with one spectrum cuboid', not visible(outline()) and
             visible(pending) and not same_outline(first_corner, pending) and diagnostic()['selection'] == 1)
    snapshot('spectrum_pending_desktop')
    click_voxel((5.5, 5.5, 8))
    region = outline(); hover((3.5, 3.5, 8))
    ui.check('completed region and independent hovered cube are both visible', diagnostic()['selection'] == 16 and
             same_outline(region, outline()) and visible(outline('cursor')) and not same_outline(region, outline('cursor')))
    ui.check('blue and spectrum edges use the same thickness',
             all(abs(a['size'][1] - b['size'][1]) < .001 for a, b in zip(region, outline('cursor'))))
    snapshot('dual_outlines_region')
    before = diagnostic()
    for mode in ('浏览', '选取', '换材质', '擦除', '吸管', '框选'):
        ui.click(mode); hover((4.5, 4.5, 8))
        ui.check(mode + ' keeps both overlays independent', same_outline(region, outline()) and visible(outline('cursor')) and
                 diagnostic()['selection'] == 16)
    ui.check('hover/mode switches never rebuild meshes or edit blocks', diagnostic()['previewBuilds'] == before['previewBuilds'] and
             diagnostic()['blocks'] == before['blocks'])

    action = next(n for n in ui.nodes('Action', ui.nodes('ViewNavigation')[0]) if n['props']['label'] == '左移')
    native = ui.call('native_control', ui.nodes('Button', action)[0]['id'])['result']
    scale = pixel_w / ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
    capture.user32.SetCursorPos(int(left + (native['global'][0] + native['size'][0]/2.) * scale),
                               int(top + (native['global'][1] + native['size'][1]/2.) * scale))
    time.sleep(.3)
    ui.check('navigation toolbar does not show a cursor through its buttons', not visible(outline('cursor')))
    finish(window, close_open, leave)


def finish(window, close_open, leave):
    hwnd = window['hwnd']
    left, top, pixel_w, pixel_h = capture._window_rect(hwnd)
    scale = pixel_w / ui.nodes('SafeArea')[0]['children'][0]['layout']['width']
    hover((3.5, 3.5, 8)); ui.click('选取')
    before = diagnostic()['pointerStats']
    close_open()
    ui.check('reopened UI detects stationary mouse without a new click', visible(outline('cursor')) and diagnostic()['pointerStats'] == before)

    # A larger hovered cube makes the interpolation observable in actual pixels.
    leave(); diagnostic({'fixture': 'solid', 'size': [4, 4, 4], 'selection': [[0, 0, 0], [0, 0, 0]], 'camera': [35, 25, 1]})
    wait_preview(); hover((2.5, 2.5, 4)); edges = outline('cursor')
    points = [p for line in edges if line['visible'] for p in line['rect']]
    crop = (int(min(p[0] for p in points)*scale)-4, int(min(p[1] for p in points)*scale)-4,
            int(max(p[0] for p in points)*scale)+5, int(max(p[1] for p in points)*scale)+5)
    with mss.MSS() as screen:
        def grab():
            assert capture.user32.GetForegroundWindow() == hwnd
            raw = screen.grab(dict(left=left, top=top, width=pixel_w, height=pixel_h))
            return Image.frombytes('RGB', raw.size, raw.bgra, 'raw', 'BGRX')
        a = grab(); time.sleep(.8); b = grab()
        a.save(ui.OUT / 'cursor_gradient_a.png'); b.save(ui.OUT / 'cursor_gradient_b.png')
        pa, pb = np.asarray(a.crop(crop)).astype(int), np.asarray(b.crop(crop)).astype(int)
        mask = (pa.max(axis=2)-pa.min(axis=2)>65) & (pa.max(axis=2)>180)
        ui.check('actual cursor pixels contain a gradient and change over time', int(mask.sum())>50 and
                 len(np.unique(pa[mask], axis=0))>30 and float(np.abs(pa-pb)[mask].mean())>8)
        Image.fromarray(np.asarray(b.crop(crop))).resize((600, 600)).save(ui.OUT / 'cursor_gradient_detail.png')

    # Real native mouse-as-touch events via F11; no patched mode or callbacks.
    leave(); ui.click('选取')
    try:
        set_touch(True)
        time.sleep(.4)
        ui.check('F11 selects the automatic touch branch before the first contact', input_state()['simulated'] and diagnostic()['touch'])
        diagnostic({'fixture': 'interior', 'size': [8, 8, 8], 'camera': [0, 0, 1]}); wait_preview()
        hover((3.5, 3.5, 8))
        region = outline('cursor')
        hover((5.5, 5.5, 8))
        ui.check('native touch has one spectrum region and no independent mouse hover',
                 visible(region) and same_outline(region, outline('cursor')) and not visible(outline()))
        touch((2.5, 2.5, 8)); single = outline('cursor')
        ui.check('native tap selects one colorful cell immediately', input_state()['mode']==1 and
                 diagnostic()['selection']==1 and visible(single) and not visible(outline()))
        hover((5.5, 5.5, 8))
        ui.check('touch selected cell stays fixed when the simulated pointer moves', same_outline(single, outline('cursor')))
        snapshot('spectrum_touch_single')
        ui.click('框选'); touch((1.5, 1.5, 8)); anchor = outline('cursor'); hover((4.5, 4.5, 8))
        ui.check('touch first corner stays as one fixed colorful cube', diagnostic()['anchor']==[1,1,7] and
                 same_outline(anchor, outline('cursor')) and not visible(outline()))
        snapshot('spectrum_touch_anchor')
        touch((4.5, 4.5, 8))
        ui.check('native touch second corner expands the spectrum into one region', diagnostic()['selection']==16 and
                 diagnostic()['anchor'] is None and visible(outline('cursor')) and not visible(outline()))
        snapshot('dual_outlines_touch')
        ui.click('选取'); touch((6.5, 6.5, 8))
        ui.check('native touch single selection replaces the spectrum region', diagnostic()['selection']==1 and
                 diagnostic()['focused']==[6,6,7] and visible(outline('cursor')) and not visible(outline()))
    finally:
        set_touch(False)
    ui.check('native mouse mode restored after touch test', not input_state()['simulated'] and not diagnostic()['touch'])
    leave()


if __name__ == '__main__':
    try:
        main()
    finally:
        name = 'dual_outlines_finish_checks.json' if '--finish' in sys.argv else 'dual_outlines_checks.json'
        (ui.OUT / name).write_text(json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')
