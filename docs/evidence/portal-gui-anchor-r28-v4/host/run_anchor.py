"""Owned legacy portal GUI2/3/4 A/B/A diagnostic; never starts a game."""
import argparse,hashlib,json,os,subprocess,sys,time,traceback
from datetime import datetime,timezone
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
PROJECT=ROOT/'.runtime/projects/portal-r28-gui-anchor-v4'
OWNER='portal-r28-gui-anchor-v4'
SCRIPTS=PROJECT/'.agents/skills/pyreact-debugging/scripts'
sys.path[:0]=[str(HERE),str(PROJECT/'tools'),str(SCRIPTS),str(PROJECT/'behavior_pack/modern_projection')]
import portal_payloads as payload
from protocol import SAMPLES,FAMILIES,ready,require_state,capture_stable,triplet,near
from camera_readback import CAMERA_READBACK
from native_ui_readback import READBACK
from native_owned_ancestry import ANCESTRY
STATE=payload.STATE+CAMERA_READBACK+READBACK+ANCESTRY+payload.GEOMETRY

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
def verify_source():
 manifest=json.loads((HERE/'source-manifest.json').read_bytes())
 assert manifest['owner']==OWNER and manifest['source_commit']=='b70ce7bf13ad6a4472f2b089ac812c162b174861'
 for key in ('files','host_files'):
  assert all(sha(PROJECT/path)==value for path,value in manifest[key].items())
 actual={p.relative_to(PROJECT).as_posix() for folder in ('behavior_pack','resource_pack') for p in (PROJECT/folder).rglob('*') if p.is_file() and p.suffix not in ('.pyc','.pyo') and '__pycache__' not in p.parts}
 assert actual==set(manifest['files'])
 assert sha(PROJECT/'.mcdev.json')==manifest['mcdev_sha256']
 bound=json.loads((HERE/'host-binding.json').read_bytes())
 assert all(sha(HERE/key)==value for key,value in bound['files'].items())
 return manifest

def main(args):
 manifest=verify_source();cutoff=datetime.fromisoformat(args.cutoff)
 assert cutoff.utcoffset() is not None and cutoff<=datetime.fromisoformat('2026-10-23T07:20:00+08:00')
 assert datetime.now(timezone.utc)<cutoff
 from _session import load_session,process_identity,desktop_lock
 from _window import _list_windows
 from mcdk import Client
 import verify_debug_blueprints as blue
 from resize_adapter import DpiApi,physical_dpi_context,resize_exact
 from resource_gate import snapshot_boundary,persist_boundary
 from lifecycle_helpers import memory,handles
 from projection.debug_portal_blueprints import source_document
 binding=load_session(args.session,OWNER,live=True)
 assert Path(binding['project']).resolve()==PROJECT
 os.environ.update(MCDEV_SESSION_FILE=binding['session_file'],MCDEV_OWNER=OWNER,MCDEV_MCP_URL=binding['mcp_url'],MCDEV_GAME_PID=str(binding['game_pid']),MCDEV_ALLOW_USER_FOREGROUND='0')
 args.output.mkdir(exist_ok=False);(args.output/'rpc').mkdir();(args.output/'resources').mkdir()
 report={'owner':OWNER,'source_commit':manifest['source_commit'],'source_manifest_sha256':sha(HERE/'source-manifest.json'),
  'started_at':datetime.now(timezone.utc).isoformat(),'families':[],'resizes':[],'cleanup_errors':[],
  'completed':False,'manual_issues_closed':0,'qualification_changed':False,'production_modified':False,
  'native_candidate_selected':False,'overlays':0,'star_density_or_animation_accepted':False,'runtime_pixels_qualified':False,
  'scope':'Only legacy default portal screen anchor. Engine TIME is allowed to change naturally.'}
 save=lambda:write(args.output/'report.json',report)
 save()
 class Check(blue.BlueprintCheck):
  def __init__(self,client):
   super().__init__(client,args.output/'report.json',25);self.cleaning=False;self.serial=0;self.previous={}
  def guard(self):
   row=load_session(args.session,OWNER,live=True)
   assert all(row.get(key)==binding.get(key) for key in ('id','owner','project','game_pid','game_identity','mcdk_pid','mcdk_identity','mcp_url'))
   sample=snapshot_boundary('cleanup' if self.cleaning else 'portal-anchor',args.assertion_status,memory,row,process_identity,handles)
   self.serial+=1;path=args.output/'resources'/('%04d.json'%self.serial)
   if self.cleaning:write(path,{'sample':sample,'cleanup_measurement_only':True})
   else:
    self.previous=persist_boundary(path,sample,OWNER,args.assertion_host_sha256,self.previous,True)
    assert datetime.now(timezone.utc)<cutoff,'Portal diagnostic cutoff reached'
  def run(self,code):
   self.guard();path=args.output/'rpc'/('%04d.py'%self.serial);path.write_text(blue.CLIENT+payload.CLIENT+code,encoding='utf8')
   value=super().run(payload.CLIENT+code);write(path.with_suffix('.result.json'),value);return value
  def state(self,family,gui,stage,expected):
   def published(value):
    if not ready(value):return False
    assert value['document']==expected,'Complete typed document changed'
    if value['theme_native_gui_scale']!=gui or value['instance_offset']!=(stage=='b'):return False
    return bool(value['portal_geometry']) and all(near(r['geometry'],r['predicted_geometry']) and
     all(near(slot['position'],r['geometry'][0]) and near(slot['size'],r['geometry'][1]) for slot in r['slots'])
     for r in value['portal_geometry'])
   value=self.wait('actual portal/camera/anchor published',published,lambda:self.run(STATE))
   require_state(value,expected,family,gui,stage);return value
  def capture(self,label):
   self.guard();path=args.output/(label+'.png')
   executable=ROOT/'.runtime/worktree-archive-r7/p0-blueprint-qa-r3/files/.runtime/native_wgc/build/Release/native_wgc_capture.exe'
   assert sha(executable)=='cb9122a6713e9c627ee9ea7658e7610e7f72d7b451412b0c6331a5bb1fbcb5a8'
   command=[sys.executable,'-B','-X','utf8',str(PROJECT/'tools/capture_native_window.py'),'--session',str(args.session),'--owner',OWNER,'--output',str(path),'--executable',str(executable)]
   result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=35)
   receipt={'command':command,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr};write(path.with_suffix('.host.json'),receipt)
   assert result.returncode==0,receipt
   from PIL import Image
   with Image.open(path) as img:size=list(img.size)
   return {'path':str(path),'sha256':sha(path),'size':size,'pixels_accepted':False}
 windows=[row for row in _list_windows() if row['pid']==binding['game_pid']];assert len(windows)==1
 hwnd=windows[0]['hwnd'];dpi=DpiApi()
 with physical_dpi_context(dpi):original_window=dpi.geometry(hwnd)
 report['original_window']=original_window;save()
 snapshot=False
 with Client(timeout=35) as client:
  check=Check(client)
  try:
   report['snapshot']=check.run(payload.SNAPSHOT);snapshot=True;save()
   for family in args.families:
    row={'family':family,'stages':[],'triplets':[],'completed':False};report['families'].append(row);save()
    expected=json.loads(json.dumps(source_document(family).to_data()))
    row['load']=check.run(payload.load(family));assert row['load']['document']==expected
    # Preview construction may still be publishing; wait before saving exact group objects.
    check.wait('default portal preview ready',ready,lambda:check.run(STATE))
    row['save_control']=check.run(payload.SAVE_CONTROL);save()
    try:
     for gui,size in SAMPLES:
      resize={}
      with desktop_lock():resize_exact(hwnd,binding['game_pid'],binding['game_identity'],*size,resize)
      report['resizes'].append(resize);save()
      deadline=time.monotonic()+20
      while True:
       value=check.wait('portal/camera after resize',ready,lambda:check.run(STATE))
       if value['theme_native_gui_scale']==gui:break
       if time.monotonic()>=deadline:raise TimeoutError('Expected native GUI %s'%gui)
       time.sleep(.2)
      states=[]
      for stage,code in (('a',None),('b',payload.APPLY),('a_return',payload.RESTORE_CONTROL)):
       item={'gui':gui,'stage':stage,'completed':False};row['stages'].append(item);save()
       if code is not None:item['switch']=check.run(code)
       before=check.state(family,gui,stage,expected);item['before']=before;save()
       item['capture']=check.capture('%s_gui%s_%s'%(family,gui,stage));save()
       assert item['capture']['size']==list(size),'Original WGC PNG dimensions differ from predeclared physical client'
       after=check.state(family,gui,stage,expected);item['after']=after;save()
       capture_stable(before,after);item['completed']=True;states.append(after);save()
      row['triplets'].append({'gui':gui,'deltas':triplet(*states,gui)});save()
    finally:
     row['method_restore']=check.run(payload.RESTORE_CONTROL);save()
     row['control_remove']=check.run(payload.REMOVE_CONTROL);save()
    row['completed']=len(row['stages'])==9;save()
   report['completed']=all(row['completed'] for row in report['families']) and len(report['families'])==len(args.families)
  except Exception as error:
   report['error']={'type':type(error).__name__,'error':str(error)};report['traceback']=traceback.format_exc();save()
  finally:
   check.cleaning=True
   if snapshot:
    for label,code in (('method_restore',payload.RESTORE_CONTROL),('session_restore',payload.RESTORE_SESSION)):
     try:report[label]=check.run(code)
     except Exception as error:report['cleanup_errors'].append({'action':label,'error':str(error)})
   try:
    restore={}
    with desktop_lock():resize_exact(hwnd,binding['game_pid'],binding['game_identity'],*original_window['client_size'],restore)
    report['window_restore']=restore;assert restore['physical_after']['client_size']==original_window['client_size']
   except Exception as error:report['cleanup_errors'].append({'action':'window_restore','error':str(error)})
   if snapshot:
    try:
     report['restore_audits']=[check.wait('original state independently restored',lambda r:r['preview_ready'],lambda:check.run(payload.AUDIT)) for unused in range(2)]
     check.run(payload.REMOVE);report['restored']=True
    except Exception as error:report['cleanup_errors'].append({'action':'restore_audit','error':str(error)})
   try:report['source_unchanged']=verify_source()==manifest
   except Exception as error:report['cleanup_errors'].append({'action':'source_unchanged','error':str(error)})
   report['finished_at']=datetime.now(timezone.utc).isoformat();save()
 print(json.dumps({key:report.get(key) for key in ('completed','restored','source_unchanged','error','cleanup_errors')}))
 return 0 if report['completed'] and report.get('restored') and report.get('source_unchanged') and not report['cleanup_errors'] else 1

if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--session',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
 parser.add_argument('--assertion-status',type=Path,required=True);parser.add_argument('--assertion-host-sha256',required=True)
 parser.add_argument('--cutoff',required=True);parser.add_argument('--families',nargs='+',choices=FAMILIES,default=list(FAMILIES))
 raise SystemExit(main(parser.parse_args()))
