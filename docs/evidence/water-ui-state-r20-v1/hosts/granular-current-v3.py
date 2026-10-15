"""Owner-bound nested elapsed-time diagnostics; retains every timing outlier."""
import hashlib
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / '.runtime/projects/water-r20'
OUTPUT = ROOT / '.runtime/water-r20-state-v7'
OWNER = 'water-r20-v7'
TARGET = OUTPUT / os.environ.get('MCDEV_WATER_GRANULAR_REPORT', 'granular-timing.json')
assert not TARGET.exists()
sys.path.insert(0, str(PROJECT / 'tools'))
import probe_product_water as probe

INSTALL = '''from modern_projection.projection.liquid_preview import LiquidPreview
from modern_projection.projection.liquid_projection import LiquidProjection
from modern_projection.projection.liquid_render import WorldLiquidRenderer
from modern_projection.projection.liquid_shape import DocumentLiquidShapes
from modern_projection.projection.liquid_face_textures import LiquidFaceTextures
from modern_projection.projection.storage import BlockStore
from modern_projection.projection.session import Session
import gc
try:
 import ctypes
 class WaterFileTime(ctypes.Structure):
  _fields_=[('low',ctypes.c_uint32),('high',ctypes.c_uint32)]
 water_thread_times=ctypes.windll.kernel32.GetThreadTimes
 water_thread_times.argtypes=[ctypes.c_void_p]+[ctypes.POINTER(WaterFileTime)]*4
 water_thread_times.restype=ctypes.c_int
 def water_thread_seconds():
  created=WaterFileTime();ended=WaterFileTime();kernel=WaterFileTime();user=WaterFileTime()
  assert water_thread_times(ctypes.c_void_p(-2),ctypes.byref(created),ctypes.byref(ended),ctypes.byref(kernel),ctypes.byref(user))
  return ((kernel.high+user.high)*4294967296.+kernel.low+user.low)*1.e-7
 water_thread_seconds()
except (ImportError,AttributeError,AssertionError):
 water_thread_seconds=None
assert not hasattr(sys,'_water_granular')
sys._water_granular={'saved':[],'stats':{},'outliers':[],'stack':[],'clock':hasattr(time,'clock'),
 'thread_cpu_supported':water_thread_seconds is not None,
 'clock_semantics':'Windows CPython 2.7 time.clock measures high-resolution elapsed wall time, not CPU time'}
def water_granular_install(cls,name):
 original=getattr(cls,name);key=cls.__name__+'.'+name
 sys._water_granular['saved'].append((cls,name,original))
 sys._water_granular['stats'][key]={'calls':0,'maximum_wall_ms':0.,'maximum_high_resolution_wall_ms':0.,'maximum_thread_cpu_ms':0.}
 def timed(self,*args,**kwargs):
  wall=time.time();fine=time.clock() if hasattr(time,'clock') else 0.
  cpu=water_thread_seconds() if water_thread_seconds else None
  row={'method':key,'started':wall,'children':[],'gc_before':gc.get_count(),
   'fixture':getattr(sys,'_blueprint_qa_identity',None)}
  if key=='Session.emit':row['field']=args[0] if args else None
  sys._water_granular['stack'].append(row)
  try:return original(self,*args,**kwargs)
  finally:
   row['wall_ms']=(time.time()-wall)*1000.
   row['high_resolution_wall_ms']=(time.clock()-fine)*1000. if hasattr(time,'clock') else None
   row['thread_cpu_ms']=(water_thread_seconds()-cpu)*1000. if water_thread_seconds else None
   row['gc_after']=gc.get_count()
   sys._water_granular['stack'].pop()
   stats=sys._water_granular['stats'][key];stats['calls']+=1
   stats['maximum_wall_ms']=max(stats['maximum_wall_ms'],row['wall_ms'])
   if row['high_resolution_wall_ms'] is not None:stats['maximum_high_resolution_wall_ms']=max(stats['maximum_high_resolution_wall_ms'],row['high_resolution_wall_ms'])
   if row['thread_cpu_ms'] is not None:stats['maximum_thread_cpu_ms']=max(stats['maximum_thread_cpu_ms'],row['thread_cpu_ms'])
   if row['wall_ms']>=5.:
    if sys._water_granular['stack']:sys._water_granular['stack'][-1]['children'].append(row)
    if len(sys._water_granular['outliers'])<256:sys._water_granular['outliers'].append(row)
 setattr(cls,name,timed)
for cls,names in ((LiquidPreview,('advance','_start','signature')),
 (LiquidProjection,('advance',)),(WorldLiquidRenderer,('advance','begin')),
 (DocumentLiquidShapes,('surface',)),(LiquidFaceTextures,('surface',)),
 (BlockStore,('copy',)),(Session,('emit',))):
 for name in names:water_granular_install(cls,name)
_result={'version':sys.version,'has_time_clock':hasattr(time,'clock')}
'''
RESTORE = '''for cls,name,original in sys._water_granular['saved']:setattr(cls,name,original)
del sys._water_granular
_result=True'''
bound = json.loads((OUTPUT / 'start.json').read_bytes())
os.environ.update(MCDEV_SESSION_FILE=bound['session_file'], MCDEV_OWNER=OWNER, MCDEV_ALLOW_USER_FOREGROUND='1')
before = probe.snapshot_sources(PROJECT)
report = {'schema':1,'diagnostic_only':True,'production_qualified':False,'completed':False,
    'restored':False,'cleanup_errors':[],'rows':[], 'source_contract_sha256':probe.snapshot_digest(before),
    'host_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client, TARGET, 45.)
    installed = timing = False
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        check.run(probe.PROFILE % (True, True))
        check.run('owner.open_workspace()\n_result=True')
        check.wait('open workspace',lambda row:row['open'] and not row['transition'],check.navigation)
        report['install'] = check.run(INSTALL)
        timing = True
        for case in ('pool','flow_west','pool','flow_east','pool','flow_west'):
            for control in ('wet','dry'):
                metrics = probe.workspace.transport.metrics(bound['session_file'], OWNER)
                if metrics['handles'] >= 225000:
                    report['budget_stop'] = metrics
                    break
                check.run(probe.LOAD % ((case,control,(35.,25.,4.6)),))
                state = check.wait('granular '+case+' '+control,
                    probe.stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                    lambda:check.run(probe.SCENE_STATE))
                report['rows'].append({'case':case,'control':control,'metrics':metrics,
                    'groups':len(state.get('liquid_groups',()))})
                probe.base.write(TARGET,report)
            if 'budget_stop' in report:break
        report['completed'] = 'budget_stop' not in report
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if timing:
            try:
                report['timing'] = check.run("_result=json.dumps(dict((k,v) for k,v in sys._water_granular.items() if k not in ('saved','stack')))")
                check.run(RESTORE)
            except Exception:
                report['cleanup_errors'].append({'phase':'timing','error':traceback.format_exc()})
        if installed:
            for label,code in (('close','if navigator.top is not None:navigator.pop()\n_result=True'),
                               ('workspace',probe.RESTORE_PROFILE)):
                try:report[label+'_restore'] = check.run(code)
                except Exception:report['cleanup_errors'].append({'phase':label,'error':traceback.format_exc()})
        report['restored'] = not report['cleanup_errors']
        report['source_unchanged'] = before == probe.snapshot_sources(PROJECT)
        probe.base.write(TARGET,report)
print(json.dumps({key:report.get(key) for key in ('completed','restored','source_unchanged','error','budget_stop')}))
raise SystemExit(0 if report['restored'] and not report.get('error') else 1)
