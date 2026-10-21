"""Exercise physical sizing and identity rejection on an invisible owned HWND."""
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path

from resize_adapter import resize_exact, user32, process_identity, foreground_identity

WORK = Path(__file__).resolve().parent


def main():
    result = {'schema': 1, 'completed': False, 'MC_started': False,
              'visible_window_created': False, 'checks': [],
              'host_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    assert user32.SetProcessDPIAware()
    user32.CreateWindowExW.argtypes = [wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR,
        wintypes.DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
        wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, ctypes.c_void_p]
    user32.CreateWindowExW.restype = wintypes.HWND
    user32.DestroyWindow.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    foreground = foreground_identity()
    # No WS_VISIBLE: this is an inert Win32 control, never a displayed test app.
    window = user32.CreateWindowExW(0x08000000, 'STATIC', 'Codex invisible sizing control',
                                  0x00CF0000, 80, 80, 300, 240, None, None, None, None)
    assert window and not user32.IsWindowVisible(window)
    pid, identity = os.getpid(), process_identity(os.getpid())
    try:
        for dimensions in ((1280, 720), (960, 600)):
            row = {}
            resize_exact(window, pid, identity, *dimensions, row)
            assert row['completed'] and row['physical_after']['client_size'] == list(dimensions)
            assert not user32.IsWindowVisible(window)
            result['checks'].append({'kind': 'actual_win32_client_size', 'dimensions': dimensions, 'result': row})
        for label, args in (('wrong_pid', (pid + 1000000, identity, 1280, 720)),
                            ('wrong_creation_identity', (pid, 'invalid-creation-identity', 1280, 720)),
                            ('invalid_size', (pid, identity, 0, 720))):
            row = {}
            try:
                resize_exact(window, *args, row)
            except (AssertionError, ValueError) as error:
                assert not row.get('mutations'), 'Negative control mutated a window'
                result['checks'].append({'kind': label, 'rejected_before_mutation': True, 'error': str(error)})
            else:
                raise AssertionError('Negative control was accepted: ' + label)
        assert foreground_identity() == foreground
        result['foreground_unchanged'] = True
        result['completed'] = True
    finally:
        assert user32.DestroyWindow(window)
        with (WORK / 'resize-desktop-controls-v1.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
    print(json.dumps({'completed': result['completed'], 'checks': len(result['checks']), 'MC_started': False}))


if __name__ == '__main__':
    main()
