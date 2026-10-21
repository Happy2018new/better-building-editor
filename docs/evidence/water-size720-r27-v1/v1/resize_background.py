"""Resize only the exact owned, non-maximized game without activation."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session, process_identity
from _window import _list_windows, _window_rect, foreground_snapshot
from resize_window import _outer_size_for_client, _monitor_work_area, user32


def main():
    binding = json.loads((WORK / 'final-source-binding-v1.json').read_bytes())
    launch = json.loads((WORK / 'launch/launch.json').read_bytes())
    os.environ.update(MCDEV_SESSION_FILE=launch['session_file'], MCDEV_OWNER=binding['owner'],
                      MCDEV_ALLOW_USER_FOREGROUND='0')
    session = load_session(launch['session_file'], binding['owner'], live=True)
    out = WORK / 'resize-background-v1.json'
    assert not out.exists()
    row = {'schema': 1, 'owner': binding['owner'], 'game_pid': session['game_pid'],
           'game_identity': session['game_identity'], 'requested_client': [1280, 720],
           'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           'completed': False, 'activation_requested': False}
    with desktop_lock():
        assert process_identity(session['game_pid']) == session['game_identity']
        windows = [w for w in _list_windows() if w['pid'] == session['game_pid']]
        assert len(windows) == 1, windows
        window = windows[0]
        hwnd = window['hwnd']
        assert not user32.IsZoomed(hwnd), 'Maximized game requires separate reviewed restore; do not activate'
        row.update(window=window, foreground_before=foreground_snapshot(), client_before=list(_window_rect(hwnd)))
        assert row['foreground_before']['pid'] != session['game_pid']
        out.write_text(json.dumps(row, indent=2) + '\n', 'utf-8')
        width, height = _outer_size_for_client(hwnd, 1280, 720)
        left, top, right, bottom = _monitor_work_area(hwnd)
        x, y = left + (right-left-width)//2, top + (bottom-top-height)//2
        flags = 0x0004 | 0x0010 | 0x0200 | 0x0020  # NOZORDER/NOACTIVATE/NOOWNERZORDER/FRAMECHANGED.
        assert user32.SetWindowPos(hwnd, 0, x, y, width, height, flags), 'SetWindowPos failed'
        time.sleep(.5)
        row.update(foreground_after=foreground_snapshot(), client_after=list(_window_rect(hwnd)))
        assert process_identity(session['game_pid']) == session['game_identity']
        assert row['client_after'][2:] == [1280, 720], row['client_after']
        assert row['foreground_after'] == row['foreground_before'], 'Foreground changed; diagnostic inadmissible'
        row['completed'] = True
        out.write_text(json.dumps(row, indent=2) + '\n', 'utf-8')
    print(json.dumps(row))


if __name__ == '__main__':
    main()
