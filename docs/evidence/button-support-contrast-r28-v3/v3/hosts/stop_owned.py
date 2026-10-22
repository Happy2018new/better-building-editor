"""Ordinary stop, same-handle exit observation, registry finalization; never force."""
import ctypes,json,subprocess,sys,time
from ctypes import wintypes
from pathlib import Path
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OWNER='r28-button-support-contrast-v3';PROJECT=ROOT/'.runtime/projects'/OWNER
SCRIPTS=PROJECT/'.agents/skills/pyreact-debugging/scripts'
sys.path.insert(0,str(SCRIPTS))
from _session import process_identity
path=Path(json.loads((HERE/'launch/report.json').read_bytes())['session_file'])
row=json.loads(path.read_bytes())
assert row['owner']==OWNER and Path(row['project']).resolve()==PROJECT.resolve()
out=HERE/'stop';out.mkdir(exist_ok=False)
report={'session_file':str(path),'binding':row,'force_executed':False,'samples':[],
 'started_at':datetime.now(timezone.utc).isoformat()}
def save():(out/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD];k.OpenProcess.restype=wintypes.HANDLE
k.GetExitCodeProcess.argtypes=[wintypes.HANDLE,ctypes.POINTER(wintypes.DWORD)]
k.GetProcessTimes.argtypes=[wintypes.HANDLE]+[ctypes.POINTER(wintypes.FILETIME)]*4
k.CloseHandle.argtypes=[wintypes.HANDLE]
held={}
def code(handle):
 value=wintypes.DWORD();assert k.GetExitCodeProcess(handle,ctypes.byref(value));return value.value
try:
 for key in ['game','mcdk']:
  handle=k.OpenProcess(0x1000,False,row[key+'_pid']);assert handle
  held[key]=handle
  times=[wintypes.FILETIME() for i in range(4)]
  assert k.GetProcessTimes(handle,*[ctypes.byref(value) for value in times])
  actual=str((times[0].dwHighDateTime<<32)|times[0].dwLowDateTime)
  assert actual==row[key+'_identity'],(actual,row[key+'_identity'])
 report['exit_before']={key:code(handle) for key,handle in held.items()};save()
 command=[sys.executable,'-B','-X','utf8',str(SCRIPTS/'instances.py'),'stop','--session',str(path),'--owner',OWNER]
 result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=35)
 report['ordinary_stop']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr};save()
 deadline=time.monotonic()+45
 while True:
  codes={key:code(handle) for key,handle in held.items()}
  report['samples'].append({'at':datetime.now(timezone.utc).isoformat(),'exit_codes':codes});save()
  if all(value!=259 for value in codes.values()):break
  if time.monotonic()>deadline:raise TimeoutError('Owned process still active after ordinary stop; no force authorized')
  time.sleep(.5)
 report['actual_exit_codes']=codes
 report['normal_shutdown_qualified']=all(value==0 for value in codes.values());save()
 result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=35)
 report['registry_finalize']={'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr}
 report['registry_final']=json.loads(path.read_bytes())
 assert report['registry_final']['state']=='stopped'
 report['completed']=True;save()
finally:
 for handle in held.values():k.CloseHandle(handle)
 save()
print(json.dumps({key:report.get(key) for key in ['completed','actual_exit_codes','normal_shutdown_qualified']}))
