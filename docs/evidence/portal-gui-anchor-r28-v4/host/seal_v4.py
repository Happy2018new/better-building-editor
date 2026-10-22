"""Seal changed V4 integration and inherited exact proofs; no process launch."""
import hashlib,json,os
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];OLD=HERE.parent/'portal-gui-anchor-v3'
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf8')
def main():
 target=HERE/'host-binding.json';assert not target.exists()
 inherited=json.loads((HERE/'inherited-controls.json').read_bytes())
 assert sha(OLD/'host-binding-final.json')==inherited['source_binding_sha256']
 oldbind=json.loads((OLD/'host-binding-final.json').read_bytes())
 assert all(sha(OLD/key)==value for key,value in oldbind['files'].items())
 assert all(sha(OLD/key)==value for key,value in inherited['controls'].items())
 manifest=json.loads((HERE/'source-manifest.json').read_bytes());project=Path(manifest['project'])
 oldmanifest=json.loads((OLD/'source-manifest.json').read_bytes());oldproject=Path(oldmanifest['project'])
 assert manifest['files']==oldmanifest['files'] and manifest['host_files']==oldmanifest['host_files']
 for mapping in ('files','host_files'):
  for key,value in manifest[mapping].items():
   assert sha(project/key)==value==sha(oldproject/key)
   assert os.path.samefile(project/key,oldproject/key)
 assert not os.path.samefile(project/'.mcdev.json',oldproject/'.mcdev.json')
 assert sha(project/'.mcdev.json')==manifest['mcdev_sha256']
 derivation=json.loads((HERE/'v3-derivation.json').read_bytes())
 time_edits=json.loads((HERE/'v7-integration.json').read_bytes())['time_maximum_declarations']
 for row in derivation['modules']:
  original=Path(row['source']);assert sha(original)==row['source_sha256']
  expected=original.read_text('utf8').replace('portal-r28-gui-anchor-v3','portal-r28-gui-anchor-v4')
  for a,b in row['declared_replacements']:expected=expected.replace(a,b)
  for edit in time_edits:
   if edit['file']==row['target']:expected=expected.replace(edit['before'],edit['after'])
  assert (HERE/row['target']).read_text('utf8')==expected,row['target']
 external=json.loads((HERE/'external-host-binding.json').read_bytes())
 assert all(sha(ROOT/key)==value for key,value in external.items())
 assert sha(HERE/'status_reader.py')=='c9383d0aedfaabdff98a52afcfe1c0d3619291d6d48138495e87f283d958e908'
 receipt=json.loads((HERE/'status-integration-controls-v1.json').read_bytes())
 assert receipt['passed'] and len(receipt['changed_entrypoints'])==2 and all(r['passed'] for r in receipt['changed_entrypoints'])
 assert not receipt['MC_started'] and not receipt['watcher_started']
 life=(HERE/'lifecycle.py').read_text('utf8');resource=(HERE/'resource_gate.py').read_text('utf8')
 assert life.count("read_status_json(HERE / 'assert-watch/status.json')")==2
 assert "json.loads((HERE / 'assert-watch/status.json').read_bytes())" not in life
 assert resource.count('read_status_json(watcher_path)')==1 and 'json.loads(Path(watcher_path).read_bytes())' not in resource
 files={p.name:sha(p) for p in HERE.glob('*.py')}
 for name in ('PLAN.md','source-manifest.json','v3-derivation.json','v7-integration.json','external-host-binding.json','inherited-controls.json'):
  files[name]=sha(HERE/name)
 controls={name:sha(HERE/name) for name in ('status-integration-controls-v1.json','lifecycle-controls-v1/first-failure.json',
  'lifecycle-controls-v2/actual-v4-start-public-status/receipt.json','status-entry-controls-v1/receipt.json')}
 binding={'schema':1,'owner':'portal-r28-gui-anchor-v4','files':files,'offline_control_receipts':controls,
  'prepared_at':datetime.now(timezone.utc).isoformat(),'MC_started':False,'watcher_started':False,'root_launch_grant_required':True,
  'manual_issues_closed':0,'native_or_pixel_acceptance':False,'V3_binding_preserved':inherited['source_binding_sha256'],
  'runtime_commit':manifest['source_commit'],'historical_helper_commit':manifest['helper_source_commit'],
  'source_hardlinks_only_to_preserved_V3':True,'runtime_config_is_independent_copy':True,
  'experimental_hard_maximum':'2026-10-23T07:20:00+08:00','watcher_hard_maximum':'2026-10-23T07:25:00+08:00'}
 write(target,binding);(HERE/'host-binding-final.json').write_bytes(target.read_bytes())
 for path in HERE.glob('*.py'):compile(path.read_bytes(),str(path),'exec')
 from run_anchor import verify_source
 verify_source()
 result={'passed':True,'owner':'portal-r28-gui-anchor-v4','runtime_files':len(manifest['files']),
  'historical_helpers':len(manifest['host_files']),'source_manifest_sha256':sha(HERE/'source-manifest.json'),
  'host_binding_sha256':sha(target),'host_objects':len(files),'changed_entrypoints_verified':2,
  'actual_status_integration_atomic_writes':200,'MC_started':False,'watcher_started':False,'launch_granted':False,
  'V3_preserved':True,'manual_issues_closed':0,'native_or_pixel_acceptance':False}
 write(HERE/'ready-receipt.json',result);print(json.dumps(result))
if __name__=='__main__':main()
