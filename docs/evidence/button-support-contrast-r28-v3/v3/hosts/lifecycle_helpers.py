import ctypes
from ctypes import wintypes
def memory():
    class Performance(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD)] + [(key, ctypes.c_size_t) for key in
            ('CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
             'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')] + [
            (key, wintypes.DWORD) for key in ('HandleCount', 'ProcessCount', 'ThreadCount')]
    api = ctypes.WinDLL('psapi', use_last_error=True)
    api.GetPerformanceInfo.argtypes = (ctypes.POINTER(Performance), wintypes.DWORD)
    api.GetPerformanceInfo.restype = wintypes.BOOL
    info = Performance()
    info.cb = ctypes.sizeof(info)
    if not api.GetPerformanceInfo(ctypes.byref(info), info.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {'committed_bytes': info.CommitTotal * info.PageSize,
            'limit_bytes': info.CommitLimit * info.PageSize,
            'headroom_bytes': (info.CommitLimit - info.CommitTotal) * info.PageSize}


def handles(pid):
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessHandleCount.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return None
    try:
        count = wintypes.DWORD()
        if not kernel.GetProcessHandleCount(handle, ctypes.byref(count)):
            raise ctypes.WinError(ctypes.get_last_error())
        return count.value
    finally:
        kernel.CloseHandle(handle)


