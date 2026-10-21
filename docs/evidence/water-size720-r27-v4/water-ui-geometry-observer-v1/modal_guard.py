"""Observe owned native modal windows; unknown content is a stop condition."""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools'))
from check_native_dialogs import assertion_dialogs
from dismiss_owned_disabled_skin_assert import known_disabled_skin_assertion
import _window


def unknown_modal_windows(pid):
    assertions = {row['hwnd']: row for row in assertion_dialogs() if row['pid'] == pid}
    user = ctypes.WinDLL('user32', use_last_error=True)
    user.GetClassNameW.argtypes = (wintypes.HWND, wintypes.LPWSTR, ctypes.c_int)
    user.GetWindow.argtypes = (wintypes.HWND, wintypes.UINT)
    user.GetWindow.restype = wintypes.HWND
    user.IsWindowEnabled.argtypes = (wintypes.HWND,)
    unknown = []
    for row in _window._list_windows_windows():
        if row['pid'] != pid:
            continue
        name = ctypes.create_unicode_buffer(256)
        user.GetClassNameW(row['hwnd'], name, len(name))
        owner = user.GetWindow(row['hwnd'], 4)
        modal = name.value == '#32770' or bool(owner and not user.IsWindowEnabled(owner))
        known = assertions.get(row['hwnd'])
        if modal and not (known and known_disabled_skin_assertion(known)):
            unknown.append(dict(row, window_class=name.value, owner_hwnd=int(owner or 0)))
    return unknown


def assertion_status_breach(work, expected_owner, pid):
    path = Path(work) / 'assert-watch/status.json'
    try:
        status = json.loads(path.read_bytes())
    except (OSError, ValueError) as error:
        return {'reason': 'assertion_watcher_status_unreadable', 'error': str(error)}
    age = (datetime.now(timezone.utc) - datetime.fromisoformat(status['checked_at'])).total_seconds()
    if status['owners'] != [expected_owner] or status['errors'] or status['other_assertions'] or not 0 <= age < 8:
        return {'reason': 'assertion_watcher_not_healthy', 'status': status, 'age_seconds': age}
    unknown = unknown_modal_windows(pid)
    if unknown:
        return {'reason': 'unknown_owned_native_modal', 'windows': unknown}
    return None
