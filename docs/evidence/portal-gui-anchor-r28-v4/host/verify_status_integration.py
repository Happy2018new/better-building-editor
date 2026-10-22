"""Two actual V4 public-status entrypoints, with real native concurrent I/O."""
import contextlib,hashlib,json,sys,threading,time,types
from datetime import datetime,timezone,timedelta
from pathlib import Path
from unittest import mock
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(HERE))
import status_reader,resource_gate,lifecycle,assigned_manifest_read
REAL_SLEEP=time.sleep
V7=HERE.parent/'water-anchor-watcher-v7'
sys.path.append(str(V7))
from atomic_json_writer import atomic_write_json
OWNER='portal-r28-gui-anchor-v4'
WATCH_SHA='9a3a4e4ca624c22459f8387877f2cff565b65f1a467b2917eb4feccaec516799'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def base():return {'schema_version':1,'owners':[OWNER],'host_sha256':WATCH_SHA,'errors':[],'other_assertions':[],
 'checked_at':datetime.now(timezone.utc).isoformat(),'sequence':0,'payload':'x'*131074}
def writer(path,row,started,done,errors,publications):
 try:
  assert started.wait(5)
  for sequence in range(1,101):
   value=dict(row,sequence=sequence,checked_at=datetime.now(timezone.utc).isoformat())
   publications.append(atomic_write_json(path,value)['replace_attempts'])
 except BaseException as error:errors.append({'type':type(error).__name__,'message':str(error),'winerror':getattr(error,'winerror',None)})
 finally:done.set()

def lifecycle_control():
 old=HERE.parent/'portal-gui-anchor-v3/verify_lifecycle.py'
 source=old.read_text('utf8').replace('.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py',
  '.runtime/round-20261023/water-anchor-watcher-v7/watch_owned_disabled_skin_assert_r28_v7.py').replace('lifecycle-controls-v1','lifecycle-controls-v2')
 # Execute the already-reviewed V3 whole-start harness with only the watcher
 # binding key adapted. Popen/OS/time stay explicit fakes; V4 start is real.
 harness=types.ModuleType('v4_inherited_lifecycle_harness');harness.__file__=str(old)
 exec(compile(source,str(old)+'<V7-binding-only>','exec'),harness.__dict__);harness.HERE=HERE
 assert Path(harness.life.__file__).resolve()==HERE/'lifecycle.py'
 calls=[];errors=[];publications=[];started=threading.Event();done=threading.Event();threads=[]
 original=status_reader._read_manifest_bytes
 def traced(path):
  calls.append(str(path))
  if not threads:
   row=json.loads(original(path));row.update(sequence=0,payload='x'*131074)
   atomic_write_json(path,row)
   thread=threading.Thread(target=writer,args=(path,row,started,done,errors,publications));threads.append(thread)
   thread.start();started.set();REAL_SLEEP(.002)
  return original(path)
 with mock.patch.object(status_reader,'_read_manifest_bytes',traced):
  try:receipt=harness.run_case('actual-v4-start-public-status')
  finally:
   started.set()
   for thread in threads:thread.join(10)
 assert len(calls)==4 and len(threads)==1 and not threads[0].is_alive() and not errors and len(publications)==100
 reportpath=HERE/'lifecycle-controls-v2/actual-v4-start-public-status/launch-v2/launch.json'
 assert json.loads(reportpath.read_bytes())['launcher_returncode']==0
 return {'entrypoint':'actual lifecycle.start (initial plus all three monitoring status reads)',
  'passed':True,'status_native_reads':len(calls),'actual_atomic_writes':len(publications),'writer_maximum_attempts':max(publications),
  'fake_boundaries':receipt['explicit_fake_boundaries'],'inherited_fixture_sha256':sha(old),
  'fixture_source_changes':['watcher external-binding key V5 to V7','fresh output directory v1 to v2'],
  'actual_lifecycle_module_path':str(Path(harness.life.__file__).resolve()),'raw_status_reads_preserved_in_fixture':False,
  'fixture_receipt':receipt,'errors':errors}

def resource_control():
 folder=HERE/'status-entry-controls-v1';folder.mkdir();path=folder/'status.json';row=base();atomic_write_json(path,row)
 started=threading.Event();done=threading.Event();errors=[];publications=[];sequences=[];samples=[]
 thread=threading.Thread(target=writer,args=(path,row,started,done,errors,publications));thread.start()
 try:
  for unused in range(100000):
   sample=resource_gate.snapshot_boundary('actual-V4-status-entry',path,lambda:{'headroom_bytes':8*1024**3})
   resource_gate.validate_boundary(sample,OWNER,WATCH_SHA)
   value=sample['watcher'];assert value['payload']==row['payload'] and 0<=value['sequence']<=100
   sequences.append(value['sequence']);started.set()
   if done.is_set() and len(sequences)>=100:break
 finally:started.set();thread.join(10)
 assert not thread.is_alive() and not errors and len(publications)==100
 assert min(sequences)==0 and max(sequences)>0 and status_reader.read_json(path)['sequence']==100
 negatives=[]
 for label,changed in (('owner',dict(row,owners=['other'])),('host-sha',dict(row,host_sha256='f'*64)),
  ('errors',dict(row,errors=['explicit failure'])),
  ('stale',dict(row,checked_at=(datetime.now(timezone.utc)-timedelta(seconds=120)).isoformat()))):
  atomic_write_json(path,changed)
  sample=resource_gate.snapshot_boundary('negative-'+label,path,lambda:{'headroom_bytes':8*1024**3})
  try:resource_gate.validate_boundary(sample,OWNER,WATCH_SHA)
  except AssertionError:negatives.append({'case':label,'rejected':True,'fresh_status_read':sample['watcher']==changed})
  else:raise AssertionError('Original guard accepted changed '+label)
 path.write_bytes(b'{')
 sample=resource_gate.snapshot_boundary('negative-json',path,lambda:{'headroom_bytes':8*1024**3})
 assert sample['watcher_error']['type']=='JSONDecodeError' and 'watcher' not in sample
 try:resource_gate.validate_boundary(sample,OWNER,WATCH_SHA)
 except AssertionError:negatives.append({'case':'malformed-json','rejected':True,'no_stale_fallback':True})
 else:raise AssertionError('Original guard accepted invalid status')
 receipt={'entrypoint':'actual resource_gate.snapshot_boundary + unchanged validate_boundary','passed':True,
  'actual_atomic_writes':len(publications),'actual_status_reads':len(sequences),
  'observed_sequence_range':[min(sequences),max(sequences)],'payload_characters':len(row['payload']),
  'writer_maximum_attempts':max(publications),'validation_negatives':negatives,'errors':errors,
  'fake_boundaries':['memory measurement only; no game/session/process requested']}
 write(folder/'receipt.json',receipt);return receipt

def main():
 target=HERE/'status-integration-controls-v1.json';assert not target.exists()
 assert Path(status_reader.__file__).resolve()==HERE/'status_reader.py'
 assert sha(HERE/'status_reader.py')=='c9383d0aedfaabdff98a52afcfe1c0d3619291d6d48138495e87f283d958e908'
 rows=[lifecycle_control(),resource_control()]
 result={'passed':True,'changed_entrypoints':rows,'reader_byte_exact_sealed_V7':True,
  'no_cache_fallback_or_validation_retry_added':True,'unchanged_business_and_assigned_read_controls_inherited':True,
  'MC_started':False,'watcher_started':False}
 write(target,result);print(json.dumps({'passed':True,'changed_entrypoints':len(rows),
  'actual_atomic_writes':sum(r['actual_atomic_writes'] for r in rows),'MC_started':False,'watcher_started':False}))
if __name__=='__main__':main()
