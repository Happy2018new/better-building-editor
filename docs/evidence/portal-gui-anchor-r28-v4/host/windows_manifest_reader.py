"""Retained-handle Win32 reads and bounded callback retries, for diagnostic hosts.

The native read preserves GetLastError. A Python errno=13 without a Windows code
is deliberately not classified as a retryable sharing failure.
"""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import time

READ_DELAYS=(.05,.1,.2,.4)
RETRY_WINERRORS=(5,32,33)


def native_read_bytes(path):
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.CreateFileW.argtypes=(wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,wintypes.LPVOID,
                                wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE)
    kernel.CreateFileW.restype=wintypes.HANDLE
    kernel.ReadFile.argtypes=(wintypes.HANDLE,wintypes.LPVOID,wintypes.DWORD,
                             ctypes.POINTER(wintypes.DWORD),wintypes.LPVOID)
    kernel.CloseHandle.argtypes=(wintypes.HANDLE,)
    # Share delete permits the writer's atomic os.replace, while this handle
    # still reads one retained file snapshot. No write/replace is performed.
    handle=kernel.CreateFileW(str(Path(path).resolve()),0x80000000,1|2|4,None,3,0,None)
    if not handle or handle==ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    parts=[]
    try:
        buffer=ctypes.create_string_buffer(65536)
        while True:
            count=wintypes.DWORD()
            if not kernel.ReadFile(handle,buffer,len(buffer),ctypes.byref(count),None):
                raise ctypes.WinError(ctypes.get_last_error())
            if not count.value:break
            parts.append(buffer.raw[:count.value])
    finally:
        kernel.CloseHandle(handle)
    return b''.join(parts)


def native_read_json(path):
    return json.loads(native_read_bytes(path))


def bounded_manifest_read(callback, events, label):
    """Retry the whole caller transaction only for measured Win32 5/32/33.

    Callback must redo its complete read/validation transaction each time.
    Other OS codes, JSON/schema/owner/identity validation failures are not
    retried. Exhaustion is recorded and re-raised for the caller's fail-closed
    policy. Events contain paths/codes/timings, never file contents.
    """
    failures=[];started=time.monotonic()
    for attempt in range(len(READ_DELAYS)+1):
        try:
            result=callback()
        except OSError as error:
            winerror=getattr(error,'winerror',None)
            if winerror not in RETRY_WINERRORS:raise
            failures.append({'attempt':attempt+1,'winerror':winerror,'errno':error.errno,
                             'elapsed_seconds':time.monotonic()-started})
            if attempt==len(READ_DELAYS):
                events.append({'label':str(label),'recovered':False,'exhausted':True,
                    'failures':failures,'elapsed_seconds':time.monotonic()-started})
                raise
            time.sleep(READ_DELAYS[attempt])
            continue
        if failures:
            events.append({'label':str(label),'recovered':True,'exhausted':False,
                'failures':failures,'successful_attempt':attempt+1,
                'elapsed_seconds':time.monotonic()-started})
        return result
    raise AssertionError('Unreachable bounded read state')
