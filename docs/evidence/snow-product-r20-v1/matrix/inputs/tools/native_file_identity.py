"""Read Windows physical paths and file IDs without loading a staging tool."""
import ctypes
from ctypes import wintypes
from pathlib import Path


def require(value, message):
    if not value:
        raise ValueError(message)


def file_identity(path, directory=False, reparse=False):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                  wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.GetFinalPathNameByHandleW.argtypes = [wintypes.HANDLE, wintypes.LPWSTR,
                                                wintypes.DWORD, wintypes.DWORD]
    kernel.GetFinalPathNameByHandleW.restype = wintypes.DWORD
    kernel.GetFileInformationByHandle.argtypes = [wintypes.HANDLE, wintypes.LPVOID]
    kernel.GetFileInformationByHandle.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    class Information(ctypes.Structure):
        _fields_ = [('attributes', wintypes.DWORD), ('created', wintypes.FILETIME),
                    ('accessed', wintypes.FILETIME), ('written', wintypes.FILETIME),
                    ('volume', wintypes.DWORD), ('size_high', wintypes.DWORD),
                    ('size_low', wintypes.DWORD), ('links', wintypes.DWORD),
                    ('index_high', wintypes.DWORD), ('index_low', wintypes.DWORD)]

    flags = (0x02000000 if directory else 0) | (0x00200000 if reparse else 0)
    handle = kernel.CreateFileW(str(path), 0x80000000, 7, None, 3, flags, None)
    require(handle != ctypes.c_void_p(-1).value, 'Cannot open file identity: ' + str(path))
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        count = kernel.GetFinalPathNameByHandleW(handle, buffer, len(buffer), 0)
        require(0 < count < len(buffer), 'Cannot resolve physical path')
        information = Information()
        require(kernel.GetFileInformationByHandle(handle, ctypes.byref(information)),
                'Cannot read file ID')
        final = buffer.value
        if final.startswith('\\\\?\\'):
            final = final[4:]
        return {'final_path': str(Path(final)), 'volume': information.volume,
                'file_id': (information.index_high << 32) | information.index_low,
                'bytes': (information.size_high << 32) | information.size_low}
    finally:
        kernel.CloseHandle(handle)
