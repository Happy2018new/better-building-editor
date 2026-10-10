"""Release inputs and minimize only the live managed game that owns this route."""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import desktop_lock, load_session
from _window import _list_windows, user32
from mcdk import Client


def main():
    session = load_session(live=True)
    with desktop_lock():
        with Client(timeout=30) as client:
            released = client.call('mc_input', {'op': '/release-all', 'args': {}})
        windows = [window for window in _list_windows() if window['pid'] == session['game_pid']]
        assert len(windows) == 1, windows
        window = windows[0]
        user32.ShowWindow(window['hwnd'], 6)
        time.sleep(.1)
        assert user32.IsIconic(window['hwnd']), window
        assert user32.GetForegroundWindow() != window['hwnd'], window
        return {'pid': session['game_pid'], 'minimized': True,
                'input_release': released, 'session': session['session_file']}


if __name__ == '__main__':
    print(json.dumps(main()))
