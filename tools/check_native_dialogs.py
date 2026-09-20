"""Detect blocking native assertions separately from the game log. Never dismiss them."""
import ctypes
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / '.agents/skills/pyreact-debugging/scripts'))
sys.path.insert(1, str(Path(__file__).resolve().parent / 'pyreact_legacy'))
import capture_screen as capture


def assertion_dialogs():
    dialogs = []
    for window in capture._list_windows():
        if 'assert' not in window['title'].lower():
            continue
        item = dict(window)
        if sys.platform == 'win32':
            children = []
            @capture.WNDENUMPROC
            def collect(hwnd, unused):
                value = capture._window_text_windows(hwnd)
                if value:
                    children.append(value)
                return True
            capture.user32.EnumChildWindows.argtypes = [ctypes.wintypes.HWND, capture.WNDENUMPROC, ctypes.wintypes.LPARAM]
            capture.user32.EnumChildWindows(window['hwnd'], collect, 0)
            item['text'] = '\n'.join(children)
        dialogs.append(item)
    return dialogs


def assert_clear():
    dialogs = assertion_dialogs()
    if dialogs:
        raise AssertionError('Native assertion dialog: ' + json.dumps(dialogs, ensure_ascii=False))


if __name__ == '__main__':
    found = assertion_dialogs()
    print(json.dumps({'assertions': found}, ensure_ascii=False, indent=2))
    sys.exit(bool(found))
