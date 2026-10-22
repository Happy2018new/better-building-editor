"""Public status reader: exact three-function extraction from _session at 94598a69f84473812938228e33a495c08f329a70."""
import ctypes
import json
import logging
import os
from pathlib import Path
import time


def _manifest_kernel():
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.ReadFile.argtypes = [wintypes.HANDLE, wintypes.LPVOID, wintypes.DWORD,
                               ctypes.POINTER(wintypes.DWORD), wintypes.LPVOID]
    kernel.ReadFile.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    return kernel


def _read_manifest_bytes(path):
    """Read one retained file snapshot with native read/write/delete sharing."""
    if os.name != "nt":
        return path.read_bytes()
    from ctypes import wintypes
    kernel = _manifest_kernel()
    # GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
    # OPEN_EXISTING. Keep the same handle for every chunk, even across replace.
    handle = kernel.CreateFileW(str(path), 0x80000000, 7, None, 3, 0x80, None)
    if handle is None or handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        chunks = []
        buffer = ctypes.create_string_buffer(65536)
        while True:
            count = wintypes.DWORD()
            if not kernel.ReadFile(handle, buffer, len(buffer), ctypes.byref(count), None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not count.value:
                return b"".join(chunks)
            chunks.append(buffer.raw[:count.value])
    finally:
        kernel.CloseHandle(handle)


def read_json(path):
    """Read a manifest, retrying only measured Win32 sharing/lock conflicts.

    Content and binding validation never use stale data or enter this retry.
    Access denied (5), errno 13 without a native code, invalid JSON and invalid
    UTF-8 are substantive failures. No process start or RPC is replayed.
    """
    path = Path(path)
    delays = (.05, .1, .2, .4)
    for attempt in range(len(delays) + 1):
        try:
            data = _read_manifest_bytes(path)
        except OSError as error:
            if getattr(error, 'winerror', None) not in (32, 33) or attempt == len(delays):
                raise
            logging.getLogger(__name__).warning(
                'Manifest read temporarily blocked (attempt %d/5, winerror=%s): %s',
                attempt + 1, error.winerror, path)
            time.sleep(delays[attempt])
        else:
            return json.loads(data.decode("utf-8"))
