"""Private Windows watcher-status I/O, synchronized across participating hosts.

Only the explicitly bound status path uses this module. Session manifests keep
the original byte-identical reader. JSON and caller validation are never retried
by the mutex. A failed or abandoned acquisition fails closed.
"""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from windows_manifest_reader import bounded_manifest_read, native_read_json

WAIT_MS = 750
WAIT_OBJECT_0 = 0
WAIT_ABANDONED = 0x80
WAIT_TIMEOUT = 0x102
WAIT_FAILED = 0xffffffff
REPLACE_DELAYS = (.05, .1, .2, .4)
RETRY_WINERRORS = (5, 32, 33)

_kernel = ctypes.WinDLL('kernel32', use_last_error=True)
_kernel.CreateMutexW.argtypes = (wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR)
_kernel.CreateMutexW.restype = wintypes.HANDLE
_kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
_kernel.WaitForSingleObject.restype = wintypes.DWORD
_kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
_kernel.ReleaseMutex.restype = wintypes.BOOL
_kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
_kernel.CloseHandle.restype = wintypes.BOOL


class StatusMutexTimeoutError(TimeoutError):
    """The separate bounded status mutex wait elapsed; do not retry it."""


class StatusMutexAbandonedError(RuntimeError):
    """Previous owner exited without release; do not trust this transaction."""


def normalized_path(path):
    return os.path.normcase(os.path.abspath(os.path.normpath(os.fspath(path))))


def mutex_name(path):
    digest = hashlib.sha256(normalized_path(path).encode('utf-8')).hexdigest()
    return 'Local\\BBE_R27_Status_v1_' + digest


@contextmanager
def status_mutex(path):
    name = mutex_name(path)
    handle = _kernel.CreateMutexW(None, False, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    acquired = False
    primary = None
    try:
        result = _kernel.WaitForSingleObject(handle, WAIT_MS)
        if result == WAIT_OBJECT_0:
            acquired = True
        elif result == WAIT_ABANDONED:
            acquired = True
            raise StatusMutexAbandonedError('Abandoned watcher status mutex: ' + name)
        elif result == WAIT_TIMEOUT:
            raise StatusMutexTimeoutError('Watcher status mutex wait exceeded 750 ms: ' + name)
        elif result == WAIT_FAILED:
            raise ctypes.WinError(ctypes.get_last_error())
        else:
            raise RuntimeError('Unexpected watcher status mutex result: ' + str(result))
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        failures = []
        if acquired and not _kernel.ReleaseMutex(handle):
            failures.append(ctypes.WinError(ctypes.get_last_error()))
        if not _kernel.CloseHandle(handle):
            failures.append(ctypes.WinError(ctypes.get_last_error()))
        if failures:
            if primary is None:
                raise failures[0]
            if hasattr(primary, 'add_note'):
                for failure in failures:
                    primary.add_note('Status mutex cleanup failure: ' + repr(failure))


def read_status_json(path, events):
    path = normalized_path(path)
    with status_mutex(path):
        return bounded_manifest_read(lambda: native_read_json(path), events, str(path))


def replace_complete(temporary, path):
    """Caller retains mutex throughout these original bounded OS-error retries."""
    for attempt in range(len(REPLACE_DELAYS) + 1):
        try:
            os.replace(temporary, path)
            return
        except OSError as error:
            if getattr(error, 'winerror', None) not in RETRY_WINERRORS or attempt == len(REPLACE_DELAYS):
                raise
            time.sleep(REPLACE_DELAYS[attempt])


def publish_status(path, status):
    path = Path(normalized_path(path))
    raw = (json.dumps(status, indent=2) + '\n').encode('ascii')
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', prefix='.' + path.name + '.',
                                         suffix='.tmp', dir=str(path.parent), delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(raw)
            stream.flush()
        with status_mutex(path):
            replace_complete(temporary, path)
    except BaseException:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                # Preserve the publication failure, never replace or truncate target.
                pass
        raise
