"""Bounded native session reads; retry only actual read failures with Win32 32/33."""
import json,time
from pathlib import Path
from windows_manifest_reader import native_read_bytes

DELAYS=(.05,.1,.2,.4)
RETRY_WINERRORS=(32,33)

class AssignedManifestReader:
 def __init__(self,owner,project,identity_reader,events,native_read=native_read_bytes,
              clock=time.monotonic,sleep=time.sleep):
  self.owner,self.project=owner,Path(project).resolve()
  self.identity_reader,self.events=identity_reader,events
  self.native_read,self.clock,self.sleep=native_read,clock,sleep
  self.path=None;self.session_id=None;self.published={}

 def read(self,path,candidate=False):
  path=Path(path).resolve()
  if self.path is not None and path!=self.path:raise ValueError('Assigned manifest path changed')
  started=self.clock();failures=[];event=None
  for index in range(len(DELAYS)+1):
   # This try covers native reading alone. Decode/schema/ownership/process
   # validation errors, including their OSError values, are never retried.
   try:raw=self.native_read(path)
   except OSError as error:
    code=getattr(error,'winerror',None)
    if code not in RETRY_WINERRORS:
     if event is not None:
      event.update(aborted=True,terminal_error_type=type(error).__name__,terminal_winerror=code,
       terminal_errno=error.errno,elapsed_seconds=self.clock()-started)
     raise
    delay=DELAYS[index] if index<len(DELAYS) else 0.
    failures.append({'attempt':index+1,'winerror':code,'errno':error.errno,
      'elapsed_seconds':self.clock()-started,'next_sleep_seconds':delay})
    if event is None:
     event={'path':str(path),'failures':failures,'recovered':False,'exhausted':False,
      'max_attempts':5,'maximum_sleep_seconds':sum(DELAYS)}
     self.events.append(event)
    event['elapsed_seconds']=self.clock()-started
    if index==len(DELAYS):
     event['exhausted']=True
     raise
    self.sleep(delay);continue
   # One retained native handle supplied the whole byte snapshot. No cached
   # document is substituted and validation runs anew for the successful read.
   try:
    data=json.loads(raw)
    result=self._validate(data,path,candidate)
   except Exception as error:
    if event is not None:
     event.update(validation_failed=True,terminal_error_type=type(error).__name__,
      successful_native_read_attempt=index+1,elapsed_seconds=self.clock()-started)
    raise
   if event is not None:event.update(recovered=True,successful_attempt=index+1,
    elapsed_seconds=self.clock()-started)
   return result
  raise AssertionError('Unreachable bounded native read state')

 def _validate(self,data,path,candidate):
  if type(data) is not dict:raise ValueError('Assigned manifest must be a JSON object')
  if self.path is None and candidate and data.get('owner')!=self.owner:return None
  if type(data.get('schema')) is not int or data['schema']!=1:raise ValueError('Invalid assigned manifest schema')
  if data.get('owner')!=self.owner:raise ValueError('Assigned manifest owner changed')
  if type(data.get('session_file')) is not str or Path(data['session_file']).resolve()!=path:
   raise ValueError('Assigned session_file path differs')
  if type(data.get('project')) is not str or Path(data['project']).resolve()!=self.project:
   raise ValueError('Assigned project path differs')
  session_id=data.get('id')
  if type(session_id) is not str or len(session_id)!=32 or any(c not in '0123456789abcdef' for c in session_id):
   raise ValueError('Invalid assigned session ID')
  if self.session_id is not None and session_id!=self.session_id:raise ValueError('Assigned session ID changed')
  if data.get('state') not in ('starting','ready','failed','stopped'):raise ValueError('Invalid assigned session state')
  published={}
  for key in ('game','mcdk'):
   pid,identity=data.get(key+'_pid'),data.get(key+'_identity')
   if pid is None and identity is None:
    if key in self.published:raise ValueError('Published process identity was removed: '+key)
    continue
   if type(pid) is not int or pid<=0 or type(identity) is not str or not identity.isdigit():
    raise ValueError('Invalid assigned process identity pair: '+key)
   pair=(pid,identity)
   if key in self.published and pair!=self.published[key]:raise ValueError('Published process identity changed: '+key)
   if self.identity_reader(pid)!=identity:raise ValueError('Assigned live process identity differs: '+key)
   published[key]=pair
  # Retain continuity facts only, never file data or stale successful rows.
  self.path,self.session_id,self.published=path,session_id,published
  return data
