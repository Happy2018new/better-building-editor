"""Release inputs and minimize only the live managed game that owns this route."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session
from _window import WNDENUMPROC, _activate_window, user32
from mcdk import Client
import ctypes
from ctypes import wintypes


def owned_game_hwnd(session):
    windows = []

    @WNDENUMPROC
    def collect(hwnd, unused):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == session['game_pid'] and user32.IsWindowVisible(hwnd):
            windows.append(int(hwnd))
        return True

    assert user32.EnumWindows(collect, 0), 'Cannot enumerate owned game window'
    assert len(windows) == 1, windows
    return windows[0]


def main():
    session = load_session(live=True)
    with desktop_lock():
        hwnd = owned_game_hwnd(session)
        if user32.IsIconic(hwnd):
            assert _activate_window(hwnd), 'Cannot resume owned game for input release'
            time.sleep(2.)
        with Client(timeout=30) as client:
            released = client.call('mc_input', {'op': '/release-all', 'args': {}})
        user32.ShowWindow(hwnd, 6)
        deadline = time.monotonic() + 2.
        while user32.GetForegroundWindow() == hwnd and time.monotonic() < deadline:
            time.sleep(.05)
        assert user32.IsIconic(hwnd), hwnd
        if user32.GetForegroundWindow() == hwnd:
            user32.GetShellWindow.restype = wintypes.HWND
            shell = user32.GetShellWindow()
            assert shell, 'Cannot find the desktop shell for focus handoff'
            assert _activate_window(shell), 'Cannot hand focus back to the desktop shell'
        assert user32.GetForegroundWindow() != hwnd, hwnd
        return {'pid': session['game_pid'], 'minimized': True,
                'input_release': released, 'session': session['session_file']}


if __name__ == '__main__':
    print(json.dumps(main()))
