"""Private launcher: retain managed readiness, use its native IPv4 ownership check."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
import instances


def discover(mcdk_pid, port, timeout=20):
    assert isinstance(mcdk_pid, int) and mcdk_pid > 0
    command = ("$ErrorActionPreference='Stop'; "
               "@(Get-CimInstance Win32_Process -Filter 'ParentProcessId=%d' | "
               "Where-Object Name -eq 'Minecraft.Windows.exe' | "
               "Select-Object -ExpandProperty ProcessId) | ConvertTo-Json -Compress") % mcdk_pid
    result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                            capture_output=True, timeout=timeout,
                            creationflags=subprocess.CREATE_NO_WINDOW)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf8', 'replace'))
    raw = result.stdout.decode('utf-8-sig').strip()
    children = json.loads(raw) if raw else []
    if not isinstance(children, list):
        children = [children]
    assert all(type(pid) is int and pid > 0 for pid in children)
    return {'children': children, 'listeners': instances.listener_owners(port)}


instances.discover = discover
sys.exit(instances.main())
