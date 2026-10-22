"""Instance binding, process identities and cross-process locks (stdlib only)."""
# Local regression lock integration: see references/projection.md.
import contextlib
import ctypes
import hashlib
import json
import logging
import os
from pathlib import Path
import tempfile
import time
import uuid


def registry_dir():
    # Keep paths stable across desktop/CLI hosts and MSIX LocalAppData redirection.
    return Path(os.environ.get("USERPROFILE", tempfile.gettempdir())) / ".pyreact-debug" / "instances"


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    # A reader without FILE_SHARE_DELETE can briefly prevent replacement on
    # Windows. Retry this same completed write, never the caller's process spawn.
    delays = (.05, .1, .2, .4)
    for attempt in range(len(delays) + 1):
        try:
            os.replace(temporary, path)
        except PermissionError as error:
            if getattr(error, 'winerror', None) not in (5, 32, 33) or attempt == len(delays):
                raise
            logging.getLogger(__name__).warning(
                'Atomic JSON replacement temporarily blocked (attempt %d/5, winerror=%s): %s',
                attempt + 1, error.winerror, path)
            time.sleep(delays[attempt])
        else:
            return


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


@contextlib.contextmanager
def file_lock(path, timeout=10):
    """OS-owned byte lock; automatically released if the owner process dies."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        deadline = time.monotonic() + timeout
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("Resource busy: " + str(path))
                time.sleep(0.05)
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle, fcntl.LOCK_UN)


def _kernel():
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    kernel.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return kernel


def _identity(kernel, handle):
    from ctypes import wintypes
    times = [wintypes.FILETIME() for _ in range(4)]
    code = wintypes.DWORD()
    if not kernel.GetProcessTimes(handle, *(ctypes.byref(t) for t in times)):
        raise OSError("GetProcessTimes failed")
    if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
        return None
    return str((times[0].dwHighDateTime << 32) | times[0].dwLowDateTime)


def process_identity(pid):
    if os.name != "nt":
        raise RuntimeError("Managed game instances require Windows")
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000, False, int(pid))
    if not handle:
        return None
    try:
        return _identity(kernel, handle)
    finally:
        kernel.CloseHandle(handle)


def terminate_owned(pid, identity):
    """Validate and terminate using the same handle, avoiding PID reuse races."""
    kernel = _kernel()
    handle = kernel.OpenProcess(0x1000 | 0x1 | 0x100000, False, int(pid))
    if not handle:
        return
    try:
        current = _identity(kernel, handle)
        if current is None:
            return
        if current != identity:
            raise RuntimeError("Process identity changed; refusing to stop pid %s" % pid)
        if not kernel.TerminateProcess(handle, 1):
            raise OSError("TerminateProcess failed")
        kernel.WaitForSingleObject(handle, 5000)
    finally:
        kernel.CloseHandle(handle)


def load_session(path=None, owner=None, live=False):
    path = path or os.environ.get("MCDEV_SESSION_FILE")
    if not path:
        return None
    path = Path(path).resolve(strict=True)
    data = read_json(path)
    if data.get("schema") != 1 or Path(data.get("session_file", "")).resolve() != path:
        raise ValueError("Invalid instance manifest")
    owner = owner or os.environ.get("MCDEV_OWNER")
    if not owner or owner != data.get("owner"):
        raise ValueError("Instance owner mismatch; pass the assigned --owner")
    if live:
        if data.get("state") != "ready":
            raise RuntimeError("Instance is not ready: " + str(data.get("state")))
        for prefix in ("mcdk", "game"):
            if (not data.get(prefix + "_identity") or
                    process_identity(data[prefix + "_pid"]) != data[prefix + "_identity"]):
                raise RuntimeError("Stale instance: " + prefix + " process exited or changed")
    return data


def artifact_dir():
    data = load_session()
    if data:
        result = Path(data["artifacts"])
    else:
        result = Path(tempfile.gettempdir()) / "pyreact-debug"
        url = os.environ.get("MCDEV_MCP_URL")
        if url:
            result /= "endpoint-" + hashlib.sha256(url.encode()).hexdigest()[:16]
    result.mkdir(parents=True, exist_ok=True)
    return result


def default_tree_path():
    return str(artifact_dir() / "ui_tree.json")


def desktop_lock(timeout=10):
    # Modern Projection's run_live_check holds this lock across a regression,
    # including child resize tools. Accept only its still-live process identity.
    parent = os.environ.get('PYREACT_DESKTOP_LOCK_PID')
    identity = os.environ.get('PYREACT_DESKTOP_LOCK_IDENTITY')
    if parent and identity and process_identity(int(parent)) == identity:
        return contextlib.nullcontext()
    return file_lock(registry_dir() / "desktop.lock", timeout)
