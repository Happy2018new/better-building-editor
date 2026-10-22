"""Derive private V4 hosts and exact b70 source from sealed V3; never launch."""
import hashlib,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
OLD=HERE.parent/'portal-gui-anchor-v3'
OWNER='portal-r28-gui-anchor-v4';PROJECT=ROOT/'.runtime/projects'/OWNER
COMMIT='b70ce7bf13ad6a4472f2b089ac812c162b174861'
MODULES=('assigned_manifest_read.py','windows_manifest_reader.py','camera_gate.py','camera_readback.py',
 'lifecycle_helpers.py','lifecycle.py','native_owned_ancestry.py','native_ui_readback.py','portal_payloads.py',
 'protocol.py','resize_adapter.py','resource_gate.py','run_anchor.py','start_watch.py')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf8')
def main():
 assert not PROJECT.exists() and not (HERE/'source-manifest.json').exists()
 oldbinding=json.loads((OLD/'host-binding-final.json').read_bytes())
 assert sha(OLD/'host-binding-final.json')=='0f308d26da9fbb1194b8dfaabbdef5712734b7b6549155270ac319395837dc62'
 assert all(sha(OLD/key)==value for key,value in oldbinding['files'].items())
 assert all(sha(OLD/key)==value for key,value in oldbinding['offline_control_receipts'].items())
 provenance=[]
 for name in MODULES:
  before=(OLD/name).read_text('utf8');after=before.replace('portal-r28-gui-anchor-v3',OWNER)
  replacements=[]
  if name=='lifecycle.py':
   replacements=[('import time\n','import time\nfrom status_reader import read_json as read_status_json\n'),
    ("json.loads((HERE / 'assert-watch/status.json').read_bytes())","read_status_json(HERE / 'assert-watch/status.json')"),
    ('.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py',
     '.runtime/round-20261023/water-anchor-watcher-v7/watch_owned_disabled_skin_assert_r28_v7.py')]
  elif name=='resource_gate.py':
   replacements=[('from pathlib import Path\n','from pathlib import Path\nfrom status_reader import read_json as read_status_json\n'),
    ('json.loads(Path(watcher_path).read_bytes())','read_status_json(watcher_path)')]
  elif name=='start_watch.py':
   replacements=[('.runtime/round-20261022/water-anchor-watcher-v5/watch_owned_disabled_skin_assert_r27_v5.py',
     '.runtime/round-20261023/water-anchor-watcher-v7/watch_owned_disabled_skin_assert_r28_v7.py')]
  for a,b in replacements:
   assert a in after,(name,a);after=after.replace(a,b)
  (HERE/name).write_text(after,encoding='utf8')
  provenance.append({'source':str(OLD/name),'source_sha256':sha(OLD/name),'target':name,
   'target_sha256':sha(HERE/name),'owner_project_adaptation':True,'declared_replacements':replacements})
  undo=after
  for a,b in reversed(replacements):undo=undo.replace(b,a)
  assert undo==before.replace('portal-r28-gui-anchor-v3',OWNER)
 # Helper origins stay historical b70; do not silently import the newer 945
 # repository _session while freezing unchanged game runtime at b70.
 prior=json.loads((OLD/'source-manifest.json').read_bytes());oldproject=Path(prior['project'])
 helpers=set(prior['host_files']);tree=subprocess.check_output(['git','ls-tree','-rz','--full-tree',COMMIT],cwd=ROOT)
 selected=[]
 for row in tree.split(b'\0'):
  if not row:continue
  head,key=row.split(b'\t',1);mode,kind,oid=head.split();key=key.decode('utf8')
  if key.startswith(('behavior_pack/','resource_pack/')) or key in helpers:
   assert kind==b'blob' and mode in (b'100644',b'100755');selected.append((key,oid.decode('ascii')))
 assert helpers<=set(key for key,oid in selected);PROJECT.mkdir(parents=True)
 proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
 files={};host={};blobs={};linked=0
 try:
  for key,oid in selected:
   proc.stdin.write((oid+'\n').encode('ascii'));proc.stdin.flush()
   actual,kind,size=proc.stdout.readline().split();assert actual.decode()==oid and kind==b'blob'
   data=proc.stdout.read(int(size));assert proc.stdout.read(1)==b'\n'
   previous=oldproject/key;assert previous.read_bytes()==data
   target=PROJECT/key;target.parent.mkdir(parents=True,exist_ok=True);os.link(previous,target)
   assert target.read_bytes()==data;linked+=len(data)
   (host if key in helpers else files)[key]=sha(target);blobs[key]=oid
 finally:
  proc.stdin.close();assert proc.wait()==0
 config=(oldproject/'.mcdev.json').read_bytes();(PROJECT/'.mcdev.json').write_bytes(config)
 manifest={'schema':1,'owner':OWNER,'project':str(PROJECT),'source_commit':COMMIT,'helper_source_commit':COMMIT,
  'files':files,'runtime_files':files,'host_files':host,'git_blobs':blobs,'mcdev_sha256':sha(PROJECT/'.mcdev.json'),
  'reload_config':json.loads(config),'runtime_exact_git_bytes':True,'hardlinked_bytes':linked,'new_source_bytes':0,
  'source_archive_created':False,'source_method':'Read every b70 Git blob; hardlink only verified equal sealed V3 bytes',
  'production_modified':False,'diagnostic_overlay_files':0,'MC_started':False,'created_at':datetime.now(timezone.utc).isoformat()}
 assert all(manifest['reload_config'][k] is False for k in ('auto_hot_reload_mods','auto_hot_reload_ui','auto_hot_reload_shaders','auto_hot_reload_materials'))
 write(HERE/'source-manifest.json',manifest)
 write(HERE/'v3-derivation.json',{'source_binding_sha256':sha(OLD/'host-binding-final.json'),
  'modules':provenance,'runtime_and_36_helpers_byte_exact_b70':True,'V3_modified':False,'MC_started':False,'watcher_started':False})
 write(HERE/'inherited-controls.json',{'source':str(OLD),'source_binding_sha256':sha(OLD/'host-binding-final.json'),
  'controls':oldbinding['offline_control_receipts'],'business_and_assigned_reader_algorithms_unchanged':True,
  'MC_started':False,'watcher_started':False})
 print(json.dumps({'passed':True,'runtime':len(files),'historical_helpers':len(host),'new_source_bytes':0,
  'hardlinked_bytes':linked,'source_manifest_sha256':sha(HERE/'source-manifest.json'),'MC_started':False,'watcher_started':False}))
if __name__=='__main__':main()
