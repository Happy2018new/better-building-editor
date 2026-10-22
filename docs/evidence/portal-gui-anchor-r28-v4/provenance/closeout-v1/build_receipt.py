"""Sanitized exact V4 run/restore/exit/source closeout, without session secrets."""
import hashlib,json,sys
from datetime import datetime,timezone
from pathlib import Path
from PIL import Image
HERE=Path(__file__).resolve().parent;WORK=HERE.parent;ROOT=WORK.parents[2]
sys.path[:0]=[str(WORK),str(ROOT/'.runtime/projects/portal-r28-gui-anchor-v4/.agents/skills/pyreact-debugging/scripts')]
from _session import process_identity
from status_reader import read_json
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_bytes())
def source_guard(folder):
 binding=read(folder/'host-binding-final.json');manifest=read(folder/'source-manifest.json');project=Path(manifest['project'])
 assert all(sha(folder/key)==value for key,value in binding['files'].items())
 assert all(sha(folder/key)==value for key,value in binding['offline_control_receipts'].items())
 assert all(sha(project/key)==value for mapping in ('files','host_files') for key,value in manifest[mapping].items())
 assert sha(project/'.mcdev.json')==manifest['mcdev_sha256']
 return {'source_manifest_sha256':sha(folder/'source-manifest.json'),'host_binding_sha256':sha(folder/'host-binding-final.json'),
  'runtime_files':len(manifest['files']),'historical_helpers':len(manifest['host_files']),'all_bound_bytes_unchanged':True}
def main():
 output=HERE/'native-closeout-v1.json';assert not output.exists()
 report=read(WORK/'native-anchor-v1/report.json');launch=read(WORK/'launch-v2/launch.json')
 stops=list(WORK.glob('stop-v2-*/stop.json'));assert len(stops)==1;stop=read(stops[0])
 exits=read(WORK/'launch-v2/exact-exit.json');retirement=read(HERE/'helper-retirement-v1.json')
 watcher=read_json(WORK/'assert-watch/status.json')
 assert report['completed'] and report['restored'] and report['source_unchanged'] and not report['cleanup_errors']
 assert len(report['restore_audits'])==2 and all(row['restored'] and row['preview_ready'] for row in report['restore_audits'])
 assert report['window_restore']['physical_after']['client_size']==report['original_window']['client_size']==[1280,720]
 assert stop['registry_final']['state']=='stopped' and not stop['force_executed']
 assert all(value is None for value in stop['independent_final_active_identity'].values())
 assert retirement['completed'] and exits['completed']
 assert not watcher['errors'] and not watcher['other_assertions']
 guards={name:source_guard(WORK.parent/name) for name in ('portal-gui-anchor-v3','portal-gui-anchor-v4')}
 images=[]
 for path in sorted((WORK/'native-anchor-v1').glob('*.png')):
  with Image.open(path) as picture:size=list(picture.size)
  images.append({'path':str(path),'sha256':sha(path),'physical_size':size})
 assert len(images)==18
 triplets=[]
 for family in report['families']:
  assert family['completed'] and len(family['stages'])==9 and len(family['triplets'])==3
  for item in family['triplets']:
   deltas=item['deltas'];actual=[d['actual_logical_dy'] for d in deltas]
   error=max(abs(d['actual_logical_dy']-d['predicted_logical_dy']) for d in deltas)
   triplets.append({'family':family['family'],'gui':item['gui'],'groups':len(deltas),
    'actual_logical_dy':actual,'max_prediction_difference':error,'predeclared_gui4_zero':item['gui']==4})
 exact={name:{key:value for key,value in row.items() if key in ('pid','identity','state','exit_code','exit_code_hex','observed_at')}
  for name,row in exits['processes'].items()}
 identities=[]
 for name,row in exact.items():
  actual=process_identity(row['pid']);assert actual!=row['identity'];identities.append({'kind':name,'pid':row['pid'],
   'expected_identity':row['identity'],'actual_active_identity':actual,'owned_identity_absent':True})
 for row in retirement['helpers']:
  actual=process_identity(row['pid']);assert actual!=row['expected_identity'];identities.append({'kind':row['kind'],
   'pid':row['pid'],'expected_identity':row['expected_identity'],'actual_active_identity':actual,'owned_identity_absent':True})
 value={'schema':1,'owner':'portal-r28-gui-anchor-v4','closed_at':datetime.now(timezone.utc).isoformat(),
  'root_grant_sha256':sha(WORK/'root-launch-grant-v4.json'),'runner_returncode':read(WORK/'native-run-finished-v1.json')['runner_returncode'],
  'completed':True,'restored':True,'restore_audits':2,'window_restored_physical':[1280,720],
  'source_guards':guards,'frames':images,'triplets':triplets,'report_sha256':sha(WORK/'native-anchor-v1/report.json'),
  'first_business_failure':None,'cleanup_errors':[],'ordinary_stop_returncode':stop['ordinary_stop']['returncode'],
  'ordinary_stop_stderr':stop['ordinary_stop']['stderr'],'ordinary_stop_grace_seconds':stop['grace_seconds'],
  'force_executed':stop['force_executed'],'registry_finalize_returncode':stop['registry_finalize']['returncode'],
  'registry_final_state':stop['registry_final']['state'],'exact_exit_codes':exact,
  'game_exit_is_abnormal':exact['game']['exit_code']!=0,'helper_retirement_sha256':sha(HERE/'helper-retirement-v1.json'),
  'helpers':[{'kind':r['kind'],'pid':r['pid'],'identity':r['expected_identity'],'terminated':r['terminated'],
   'exit_after':r.get('exit_after'),'already_absent':r.get('already_absent',False)} for r in retirement['helpers']],
  'exact_owned_identities_absent':identities,'watcher_errors':watcher['errors'],'watcher_other_assertions':watcher['other_assertions'],
  'watcher_known_assert_recoveries':len(watcher['known_assert_recoveries']),
  'watcher_manifest_read_events':watcher['manifest_read_events'],'startup_assigned_manifest_read_events':launch['manifest_read_events'],
  'slot_release_ready':True,'manual_issues_closed':0,'pixels_or_animation_qualified':False,
  'production_or_qualification_modified':False}
 output.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
 print(json.dumps({'receipt':str(output),'sha256':sha(output),'frames':18,'restore_audits':2,'V3_V4_sources_unchanged':True,
  'ordinary_stop_returncode':value['ordinary_stop_returncode'],'force_executed':False,'game_exit':exact['game']['exit_code_hex'],
  'mcdk_exit':exact['mcdk']['exit_code_hex'],'helpers_retired':True,'slot_release_ready':True}))
if __name__=='__main__':main()
