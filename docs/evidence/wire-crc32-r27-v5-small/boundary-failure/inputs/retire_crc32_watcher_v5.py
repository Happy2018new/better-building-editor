"""Retire only the exact approved CRC diagnostic watcher after ordinary game stop."""
import ctypes
from ctypes import wintypes
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from _session import _identity, _kernel, process_identity, terminate_owned

folder = HERE / 'launch-v5'
output = folder / 'watcher-stop-v6.json'
assert not output.exists()
stop = json.loads((folder / 'stop.json').read_bytes())
assert stop['ordinary_returncode'] == 0 and stop['still_live'] is False
exit_report = json.loads((folder / 'exact-exit.json').read_bytes())
assert exit_report['completed']
assert all(row['state'] == 'exited' for row in exit_report['processes'].values())
binding = json.loads((folder / 'watch-binding.json').read_bytes())
launch = json.loads((folder / 'launch.json').read_bytes())
owner = 'wire-r27-crc32-phase-v5'
assert launch['owner'] == owner
pid, identity = binding['watcher_pid'], binding['watcher_identity']
assert pid == 8024 and identity == '134370904623999936'
assert process_identity(launch['game_pid']) is None
assert process_identity(launch['mcdk_pid']) is None
process = json.loads(subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
    'Get-CimInstance Win32_Process -Filter "ProcessId=%d" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress' % pid],
    encoding='utf8'))
assert process['ProcessId'] == pid
assert '--owner ' + owner in process['CommandLine']
assert 'watch_owned_disabled_skin_assert_r27_v5.py' in process['CommandLine']
kernel = _kernel()
handle = kernel.OpenProcess(0x1000 | 0x100000, False, pid)
assert handle
try:
    assert _identity(kernel, handle) == identity
    terminate_owned(pid, identity)
    assert kernel.WaitForSingleObject(handle, 5000) == 0
    code = wintypes.DWORD()
    assert kernel.GetExitCodeProcess(handle, ctypes.byref(code))
    actual_exit = code.value
finally:
    kernel.CloseHandle(handle)
assert process_identity(pid) is None
raw = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
    '@(Get-Process -Name Minecraft.Windows -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id) | ConvertTo-Json -Compress'],
    text=True).strip()
pids = json.loads(raw) if raw else []
if isinstance(pids, int):
    pids = [pids]
live = [{'pid': value, 'identity': current} for value in pids for current in [process_identity(value)] if current]
report = {'watcher_pid': pid, 'watcher_identity': identity,
          'actual_exit_code': actual_exit, 'actual_exit_code_hex': '0x%08X' % actual_exit,
          'reason': 'Owned diagnostic watcher has no cooperative stop interface; exact identity cleanup after ordinary game/MCDK stop',
          'game_live_identity': process_identity(launch['game_pid']),
          'mcdk_live_identity': process_identity(launch['mcdk_pid']),
          'watcher_live_identity': process_identity(pid), 'all_genuinely_live_MC': live,
          'checked_at': datetime.now(timezone.utc).isoformat()}
with output.open('xb') as stream:
    stream.write((json.dumps(report, indent=2) + '\n').encode('ascii'))
print(json.dumps(report))
