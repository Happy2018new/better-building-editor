"""Retire only this final owner's helper after game/MCDK registry finalization."""
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess,time
HERE=Path(__file__).resolve().parent
stop=json.loads((HERE/'stop/report.json').read_bytes())
assert stop['completed'] and stop['registry_final']['state']=='stopped'
start=json.loads((HERE/'assert-watch-start.json').read_bytes())
PID=start['watcher_pid'];IDENTITY=start['watcher_identity'];OWNER='r25-t02-normal-v1'
report={'pid':PID,'expected_creation_identity':IDENTITY,'owner':OWNER,'game_process_touched':False,
 'started_at':datetime.now(timezone.utc).isoformat(),'completed':False}
path=HERE/'assert-watch-close.json';assert not path.exists()
def save():path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
save()
raw=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
 'Get-CimInstance Win32_Process -Filter "ProcessId=%d" | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'%PID],text=True,encoding='utf8')
row=json.loads(raw);report['process_query']=row
assert row['ProcessId']==PID and '--owner '+OWNER in row['CommandLine']
assert 'watch_owned_disabled_skin_assert_r20.py' in row['CommandLine']
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
k.TerminateProcess.argtypes=[wintypes.HANDLE,wintypes.UINT];k.CloseHandle.argtypes=[wintypes.HANDLE]
handle=k.OpenProcess(0x1001,False,PID);assert handle
try:
 values=[wintypes.FILETIME() for unused in range(4)]
 assert k.GetProcessTimes(handle,*[ctypes.byref(value) for value in values])
 identity=str((values[0].dwHighDateTime<<32)|values[0].dwLowDateTime)
 report['actual_creation_identity']=identity;assert identity==IDENTITY
 code=wintypes.DWORD();assert k.GetExitCodeProcess(handle,ctypes.byref(code));assert code.value==259
 assert k.TerminateProcess(handle,0)
 deadline=time.monotonic()+5
 while True:
  assert k.GetExitCodeProcess(handle,ctypes.byref(code))
  if code.value!=259:break
  if time.monotonic()>deadline:raise TimeoutError('Retired final-owner observer remains active')
  time.sleep(.05)
 report.update(actual_exit_code=code.value,completed=True)
finally:k.CloseHandle(handle);save()
print(json.dumps(report))
