"""Read bound window geometry in logical and physical DPI contexts, without capture."""
import argparse
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
import os
from pathlib import Path

PER_MONITOR_V2 = ctypes.c_void_p(-4).value


class DpiApi:
    def __init__(self):
        if os.name != 'nt':
            raise RuntimeError('Window DPI geometry inspection requires Windows')
        self.user32 = ctypes.WinDLL('user32', use_last_error=True)
        self.dwm = ctypes.WinDLL('dwmapi', use_last_error=True)
        for name in ('GetThreadDpiAwarenessContext', 'GetWindowDpiAwarenessContext',
                     'SetThreadDpiAwarenessContext'):
            getattr(self.user32, name).restype = wintypes.HANDLE
        self.user32.GetWindowDpiAwarenessContext.argtypes = [wintypes.HWND]
        self.user32.SetThreadDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        self.user32.GetAwarenessFromDpiAwarenessContext.argtypes = [wintypes.HANDLE]
        self.user32.GetAwarenessFromDpiAwarenessContext.restype = ctypes.c_int
        self.user32.AreDpiAwarenessContextsEqual.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.user32.AreDpiAwarenessContextsEqual.restype = wintypes.BOOL
        self.user32.GetDpiForWindow.argtypes = [wintypes.HWND]
        self.user32.GetDpiForWindow.restype = wintypes.UINT
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetClientRect.restype = wintypes.BOOL
        self.user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
        self.user32.GetWindowRect.restype = wintypes.BOOL
        self.user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
        self.user32.ClientToScreen.restype = wintypes.BOOL
        self.dwm.DwmGetWindowAttribute.argtypes = [wintypes.HWND, wintypes.DWORD,
                                                  ctypes.c_void_p, wintypes.DWORD]
        self.dwm.DwmGetWindowAttribute.restype = ctypes.c_long

    def current(self):
        value = self.user32.GetThreadDpiAwarenessContext()
        if not value:
            raise ctypes.WinError(ctypes.get_last_error())
        return value

    def set(self, context):
        return self.user32.SetThreadDpiAwarenessContext(context)

    def equal(self, first, second):
        return bool(self.user32.AreDpiAwarenessContextsEqual(first, second))

    def describe(self, context):
        awareness = self.user32.GetAwarenessFromDpiAwarenessContext(context)
        if awareness < 0:
            raise RuntimeError('Invalid DPI awareness context')
        return {'context': context, 'awareness': awareness,
                'per_monitor_v2': self.equal(context, PER_MONITOR_V2)}

    def geometry(self, hwnd):
        client, window, bounds, origin = wintypes.RECT(), wintypes.RECT(), wintypes.RECT(), wintypes.POINT()
        if not self.user32.GetClientRect(hwnd, ctypes.byref(client)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.user32.ClientToScreen(hwnd, ctypes.byref(origin)):
            raise ctypes.WinError(ctypes.get_last_error())
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(window)):
            raise ctypes.WinError(ctypes.get_last_error())
        hr = self.dwm.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(bounds), ctypes.sizeof(bounds))
        if hr:
            raise OSError(hr, 'DwmGetWindowAttribute extended physical bounds failed')
        context = self.user32.GetWindowDpiAwarenessContext(hwnd)
        dpi = self.user32.GetDpiForWindow(hwnd)
        if not context or not dpi:
            raise RuntimeError('Window DPI context or DPI is unavailable')
        return {'thread': self.describe(self.current()), 'window_context': self.describe(context),
            'window_dpi': dpi, 'client_size': [client.right - client.left, client.bottom - client.top],
            'client_screen_origin': [origin.x, origin.y],
            'window_rect': [window.left, window.top, window.right, window.bottom],
            'dwm_physical_bounds': [bounds.left, bounds.top, bounds.right, bounds.bottom]}


@contextmanager
def physical_dpi_context(api=None):
    api = api if api is not None else DpiApi()
    original = api.current()
    previous = api.set(PER_MONITOR_V2)
    if not previous:
        raise RuntimeError('Could not enter physical Per-Monitor V2 DPI context')
    try:
        if not api.equal(previous, original) or not api.equal(api.current(), PER_MONITOR_V2):
            raise RuntimeError('Physical DPI context entry did not match the calling thread')
        yield api
    finally:
        restored = api.set(previous)
        if not restored or not api.equal(api.current(), original):
            raise RuntimeError('Could not restore the original thread DPI context')


def inspect(session_file, owner, project, api=None, host=None):
    import observe_owned_startup as observer
    report = {'schema': 1, 'ok': False, 'scope': 'Bound window geometry only',
        'started_at': datetime.now(timezone.utc).isoformat(), 'game_or_mcdk_launched': False,
        'wgc_or_sdk_called': False, 'window_mutation_attempted': False,
        'production_acceptance': False, 'dpi_virtualization_observed': False}
    try:
        session, manifest = observer.read_bound_session(session_file, owner, project)
        host = host if host is not None else observer.WindowsHost()
        api = api if api is not None else DpiApi()
        report.update(session_id=session['id'], manifest=manifest, owner=owner,
                      game_pid=session['game_pid'], game_identity=session['game_identity'])
        report['processes_before'] = observer.validate_processes(session, host.inspect_process)
        report['guard_before'] = host.guard(session)
        window = observer.guarded_window(session, report['guard_before'])
        original = api.current()
        report['default_geometry'] = api.geometry(window['hwnd'])
        with physical_dpi_context(api):
            report['physical_guard'] = host.guard(session)
            physical_window = observer.guarded_window(session, report['physical_guard'])
            report['physical_geometry'] = api.geometry(window['hwnd'])
            if physical_window['hwnd'] != window['hwnd']:
                raise RuntimeError('Physical DPI guard selected a different window')
            if [physical_window['width'], physical_window['height']] != report['physical_geometry']['client_size']:
                raise RuntimeError('Physical guard and physical client geometry differ')
        report['thread_context_restored'] = api.equal(api.current(), original)
        after, report['manifest_after'] = observer.read_bound_session(session_file, owner, project)
        for key in ('id', 'game_pid', 'game_identity', 'mcdk_pid', 'mcdk_identity', 'game_executable', 'noactivation'):
            if after.get(key) != session.get(key):
                raise RuntimeError('Bound session changed during geometry inspection: ' + key)
        report['processes_after'] = observer.validate_processes(after, host.inspect_process)
        report['guard_after'] = host.guard(session)
        current = observer.guarded_window(after, report['guard_after'])
        if any(current[key] != window[key] for key in ('hwnd', 'width', 'height')):
            raise RuntimeError('Owned window changed during geometry inspection')
        default, physical = report['default_geometry'], report['physical_geometry']
        report['dpi_virtualization_observed'] = (default['thread']['awareness'] == 0
            and physical['thread']['per_monitor_v2'] and report['thread_context_restored']
            and default['client_size'] != physical['client_size'])
        report['ok'] = True
    except Exception as error:
        report['error'] = '%s: %s' % (type(error).__name__, error)
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('DPI geometry evidence must use a fresh output path')
    report = inspect(args.session, args.owner, args.project)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='ascii') as target:
        target.write(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
