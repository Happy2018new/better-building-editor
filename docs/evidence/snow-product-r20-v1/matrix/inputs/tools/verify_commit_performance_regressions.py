"""Native regressions after batching UI commits; preserve draft, mode and window."""
import json
import subprocess
import sys
import time
import verify_ui as ui
import capture_screen as capture
from verify_font_share_polish import game
from native_input_mode import set_touch, state
from profile_editor_workflows import settle
import verify_native_touch
import verify_presence_motion
import verify_catalogue_input


def main():
    capture.user32.SetProcessDPIAware()
    window = capture._find_game_window(capture._list_windows(), process_name='Minecraft.Windows.exe')
    assert window and capture._activate_window(window['hwnd'])
    original_size = capture._window_rect(window['hwnd'])[2:]
    original_touch = state()['simulated']
    game('''fields=('editor','name','page','tool','direct_mode','group','inspector','section','solo_layer',
'canvas_x','canvas_z','focused','box_anchor','paste_origin','paste_pinned','camera_yaw','camera_pitch',
'zoom','camera_pan','camera_pivot','camera_depth','camera_depth_pose','camera_pose','focus_view','query')
api._commit_regression_saved=dict((k,getattr(s,k)) for k in fields)
_result=True''')
    try:
        verify_native_touch.main()
        set_touch(False)
        # Restore the original building for animation/resize and search checks.
        game('''for k,v in api._commit_regression_saved.items():setattr(s,k,v)
s.camera_revision+=1
s.refresh_preview();s.emit()
_result=True''')
        settle()
        verify_presence_motion.main()
        verify_catalogue_input.main()
        ui.assert_clear()
    finally:
        game('''s.cancel_edit()
s.edit_job=None
for k,v in api._commit_regression_saved.items():setattr(s,k,v)
del api._commit_regression_saved
s.camera_revision+=1
s.refresh_preview();s.emit()
_result=True''')
        set_touch(original_touch)
        current_size = capture._window_rect(window['hwnd'])[2:]
        if current_size != original_size:
            subprocess.run([sys.executable, '-X', 'utf8', str(ui.ROOT /
                '.agents/skills/pyreact-debugging/scripts/resize_window.py'),
                '--size', '%dx%d' % tuple(original_size)], check=True, capture_output=True)
            time.sleep(.5)
        settle()
        (ui.OUT/'perf67_commit_regressions.json').write_text(
            json.dumps(ui.checks, ensure_ascii=False, indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
