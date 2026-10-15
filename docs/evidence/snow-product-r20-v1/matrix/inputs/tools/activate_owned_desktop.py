"""Restore the validated session's window, including an intentionally hidden HWND."""
import ctypes
import json
from ctypes import wintypes

import verify_debug_blueprints
from _session import desktop_lock, load_session
from _window import WNDENUMPROC, _activate_window, _window_rect_windows, _window_text_windows, user32


def main():
    with desktop_lock():
        session = load_session(live=True)
        assert session is not None, 'A managed session is required'
        windows = []

        @WNDENUMPROC
        def collect(hwnd, _):
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value != session['game_pid']:
                return True
            title = _window_text_windows(hwnd)
            if not title:
                return True
            x, y, width, height = _window_rect_windows(hwnd)
            windows.append({'hwnd': int(hwnd), 'pid': pid.value, 'title': title,
                            'size': [width, height]})
            return True

        assert user32.EnumWindows(collect, 0), 'EnumWindows failed'
        game_windows = [window for window in windows if 'minecraft' in window['title'].lower()]
        assert len(game_windows) == 1, windows
        window = game_windows[0]
        load_session(live=True)
        user32.ShowWindow(window['hwnd'], 9)
        activated = _activate_window(window['hwnd'])
        assert activated, window
        print(json.dumps({'ok': True, 'activated': activated, 'window': window}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
