"""Physical client sizing using the existing border helper, without activation."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
sys.path.insert(0, str(ROOT / 'tools'))
from _session import process_identity
from _window import foreground_snapshot
from resize_window import _outer_size_for_client, user32
from diagnose_window_dpi import DpiApi, physical_dpi_context

FLAGS = 0x0002 | 0x0004 | 0x0010 | 0x0200 | 0x0020


def foreground_identity():
    return {key: value for key, value in foreground_snapshot().items() if key in ('hwnd', 'pid', 'identity')}


def resize_exact(hwnd, pid, identity, width, height, receipt):
    if type(width) is not int or type(height) is not int or not (64 <= width <= 8192 and 64 <= height <= 8192):
        raise ValueError('Unsupported client dimensions')
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD

    def check_identity():
        observed = wintypes.DWORD()
        assert user32.GetWindowThreadProcessId(hwnd, ctypes.byref(observed))
        assert observed.value == pid, 'Window PID differs from exact owner'
        assert process_identity(pid) == identity, 'Process creation identity differs'
        assert not user32.IsZoomed(hwnd), 'Maximized window is outside this reviewed resize'

    check_identity()
    dpi = DpiApi()
    receipt.update(requested_client=[width, height], activation_requested=False,
                   window_identity={'hwnd': hwnd, 'pid': pid, 'creation_identity': identity},
                   logical_before=dpi.geometry(hwnd), foreground_before=foreground_identity(),
                   resize_flags=FLAGS, mutations=[])
    with physical_dpi_context(dpi):
        receipt['physical_before'] = dpi.geometry(hwnd)
        outer_width, outer_height = _outer_size_for_client(hwnd, width, height)
        receipt['existing_border_helper_outer_size'] = [outer_width, outer_height]
        # At most one physical border correction, in case DPI-specific nonclient metrics differ.
        for attempt in range(2):
            check_identity()
            assert user32.SetWindowPos(hwnd, 0, 0, 0, outer_width, outer_height, FLAGS), 'SetWindowPos failed'
            time.sleep(.2)
            actual = dpi.geometry(hwnd)
            receipt['mutations'].append({'attempt': attempt + 1, 'requested_outer': [outer_width, outer_height],
                                         'physical_readback': actual})
            if actual['client_size'] == [width, height]:
                break
            rectangle = actual['window_rect']
            outer_width = rectangle[2] - rectangle[0] + width - actual['client_size'][0]
            outer_height = rectangle[3] - rectangle[1] + height - actual['client_size'][1]
        receipt['physical_after'] = dpi.geometry(hwnd)
        check_identity()
        assert receipt['physical_after']['client_size'] == [width, height], 'Actual physical client size differs'
    receipt['logical_after'] = dpi.geometry(hwnd)
    receipt['foreground_after'] = foreground_identity()
    assert receipt['foreground_after'] == receipt['foreground_before'], 'Foreground changed during resize'
    receipt['completed'] = True
    return receipt
