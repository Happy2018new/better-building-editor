"""Read-only actual-live Minecraft count and available system commit."""
import argparse
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    class MemoryStatus(ctypes.Structure):
        _fields_ = [('length', wintypes.DWORD), ('load', wintypes.DWORD)] + [
            (name, ctypes.c_ulonglong) for name in ('total_physical', 'available_physical',
             'total_pagefile', 'available_pagefile', 'total_virtual', 'available_virtual', 'available_extended')]
    memory = MemoryStatus()
    memory.length = ctypes.sizeof(memory)
    assert kernel.GlobalMemoryStatusEx(ctypes.byref(memory))
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
         '@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress'], text=True, encoding='utf8')
    pids = json.loads(raw) if raw.strip() else []
    if isinstance(pids, int):
        pids = [pids]
    observations = []
    for pid in pids:
        process = kernel.OpenProcess(0x1000, False, pid)
        item = {'pid': pid, 'actual_live': False}
        if process:
            try:
                code = wintypes.DWORD()
                assert kernel.GetExitCodeProcess(process, ctypes.byref(code))
                item.update(exit_code=code.value, actual_live=code.value == 259)
            finally:
                kernel.CloseHandle(process)
        observations.append(item)
    result = {'schema': 1, 'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'available_commit_bytes': memory.available_pagefile, 'available_commit_GiB': memory.available_pagefile / 1024. ** 3,
              'actual_live_MC': sum(item['actual_live'] for item in observations), 'observations': observations,
              'process_or_window_mutated': False}
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='ascii')
    print(json.dumps({key: value for key, value in result.items() if key != 'observations'}))


if __name__ == '__main__':
    main()
