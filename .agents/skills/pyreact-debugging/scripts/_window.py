# -*- coding: utf-8 -*-
"""Windows window helpers for the supplemental client-area resize tool."""

from __future__ import print_function

import ctypes
from ctypes import wintypes
from contextlib import contextmanager
import json
import os
import sys


IS_WINDOWS = os.name == "nt"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
else:
    user32 = None
    kernel32 = None

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_RESTORE = 9
WS_EX_NOACTIVATE = 0x08000000


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


if IS_WINDOWS:
    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.IsWindow.argtypes = [wintypes.HWND]
    user32.IsWindow.restype = wintypes.BOOL
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.IsIconic.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.AttachThreadInput.argtypes = [wintypes.DWORD, wintypes.DWORD, wintypes.BOOL]
    user32.AttachThreadInput.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
    user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.GetCurrentThreadId.restype = wintypes.DWORD
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    get_window_long = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
    get_window_long.argtypes = [wintypes.HWND, ctypes.c_int]
    get_window_long.restype = ctypes.c_ssize_t


def _emit(payload):
    text = json.dumps(payload, ensure_ascii=False)
    if sys.version_info[0] >= 3:
        sys.stdout.buffer.write((text + "\n").encode("utf-8"))
    else:
        sys.stdout.write((text + "\n").encode("utf-8"))


def _window_text_windows(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    if length <= 0:
        return u""
    buffer_ = ctypes.create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, buffer_, length + 1)
    return buffer_.value


def _process_name_windows(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return u""
    try:
        size = wintypes.DWORD(32768)
        path = ctypes.create_unicode_buffer(size.value)
        query = getattr(kernel32, "QueryFullProcessImageNameW", None)
        if not query or not query(handle, 0, path, ctypes.byref(size)):
            return u""
        return os.path.basename(path.value)
    finally:
        kernel32.CloseHandle(handle)


def _window_rect_windows(hwnd, include_frame=False):
    if include_frame:
        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("GetWindowRect failed")
        return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top

    rect = RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetClientRect failed")
    origin = POINT(0, 0)
    if not user32.ClientToScreen(hwnd, ctypes.byref(origin)):
        raise RuntimeError("ClientToScreen failed")
    return origin.x, origin.y, rect.right - rect.left, rect.bottom - rect.top


def _list_windows_windows():
    windows = []

    @WNDENUMPROC
    def callback(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        title = _window_text_windows(hwnd)
        if not title:
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        try:
            x, y, width, height = _window_rect_windows(hwnd)
        except RuntimeError:
            return True
        if width <= 1 or height <= 1:
            return True
        windows.append({
            "hwnd": int(hwnd),
            "pid": int(pid.value),
            "process": _process_name_windows(pid.value),
            "title": title,
            "x": x,
            "y": y,
            "width": width,
            "height": height,
            "minimized": bool(user32.IsIconic(hwnd)),
        })
        return True

    if not user32.EnumWindows(callback, 0):
        raise RuntimeError("EnumWindows failed")
    return windows


def _find_game_window(windows, pid=None, title=None, process_name=None):
    candidates = windows
    if pid is not None:
        candidates = [item for item in candidates if item["pid"] == pid]
    if title:
        title_lower = title.lower()
        candidates = [item for item in candidates if title_lower in item["title"].lower()]
    if process_name:
        process_lower = process_name.lower()
        process_matches = [
            item for item in candidates
            if item["process"].lower() == process_lower
        ]
        candidates = process_matches
    if not candidates:
        return None
    if len({item["pid"] for item in candidates}) > 1:
        raise RuntimeError("Multiple game processes match; bind a session or pass an explicit --pid")
    return max(candidates, key=lambda item: item["width"] * item["height"])


def foreground_snapshot():
    from _session import process_identity
    hwnd = user32.GetForegroundWindow()
    pid = wintypes.DWORD()
    if hwnd:
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {'hwnd': int(hwnd or 0), 'pid': int(pid.value),
            'process': _process_name_windows(pid.value) if pid.value else '',
            'identity': process_identity(pid.value) if pid.value else None,
            'title': _window_text_windows(hwnd) if hwnd else '',
            'visible': bool(hwnd and user32.IsWindowVisible(hwnd)),
            'minimized': bool(hwnd and user32.IsIconic(hwnd))}


def validate_foreground_snapshot(snapshot):
    from _session import process_identity
    hwnd, pid = snapshot.get('hwnd'), snapshot.get('pid')
    if not hwnd or not pid or not snapshot.get('identity') or not user32.IsWindow(hwnd):
        return False
    current_pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(current_pid))
    return (current_pid.value == pid and process_identity(pid) == snapshot['identity']
            and _process_name_windows(pid) == snapshot.get('process')
            and bool(user32.IsWindowVisible(hwnd)) and not user32.IsIconic(hwnd))


def user_foreground_allowed():
    return os.environ.get('MCDEV_ALLOW_USER_FOREGROUND') == '1'


@contextmanager
def physical_window_coordinates():
    """Match native WGC's client pixels without changing process-wide DPI policy."""
    setter = getattr(user32, 'SetThreadDpiAwarenessContext', None)
    if setter is None:
        raise RuntimeError('Physical window coordinates require thread DPI awareness support')
    setter.argtypes = [ctypes.c_void_p]
    setter.restype = ctypes.c_void_p
    previous = setter(ctypes.c_void_p(-4))
    if not previous:
        raise RuntimeError('Could not enter per-monitor-v2 window coordinates')
    try:
        yield
    finally:
        if not setter(previous):
            raise RuntimeError('Could not restore thread DPI awareness')


def foreground_policy_satisfied(guard, pid):
    foreground_pid = guard.get('foreground', {}).get('pid')
    if type(foreground_pid) is not int or foreground_pid < 0:
        return False
    background = foreground_pid != pid
    if guard.get('background_safe') is not background:
        return False
    return background or user_foreground_allowed()


def background_guard_state(pid, process_name):
    """Inspect the owned windows without showing, resizing or activating them."""
    windows = [window for window in _list_windows_windows()
               if window['pid'] == pid and window['process'].lower() == process_name.lower()]
    foreground = foreground_snapshot()
    for window in windows:
        window['noactivate'] = bool(get_window_long(window['hwnd'], -20) & WS_EX_NOACTIVATE)
    return {'foreground': foreground, 'windows': windows,
            'background_safe': foreground['pid'] != pid,
            'window_noactivate': bool(windows) and all(window['noactivate'] for window in windows)}


def _activate_window(hwnd):
    """Best-effort foreground activation after resizing."""
    foreground = user32.GetForegroundWindow()
    current_thread = kernel32.GetCurrentThreadId()
    foreground_thread = 0
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)
    attached_foreground = False
    attached_target = False
    try:
        if foreground:
            foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
        if foreground_thread and foreground_thread != current_thread:
            attached_foreground = bool(user32.AttachThreadInput(
                current_thread, foreground_thread, True,
            ))
        if target_thread and target_thread != current_thread:
            attached_target = bool(user32.AttachThreadInput(
                current_thread, target_thread, True,
            ))
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, SW_RESTORE)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)
    finally:
        if attached_target:
            user32.AttachThreadInput(current_thread, target_thread, False)
        if attached_foreground:
            user32.AttachThreadInput(current_thread, foreground_thread, False)
    return user32.GetForegroundWindow() == hwnd



_window_rect = _window_rect_windows
_list_windows = _list_windows_windows
