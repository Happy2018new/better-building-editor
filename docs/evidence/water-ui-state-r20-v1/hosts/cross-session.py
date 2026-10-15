"""Three guarded public pool pixels in an existing owner-bound session."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

parser = argparse.ArgumentParser(description=__doc__)
for name in ('project','session','owner','capture-exe','output'):
    parser.add_argument('--'+name,required=True)
args = parser.parse_args()
project = Path(args.project).resolve(strict=True)
target = Path(args.output)
if target.exists():
    raise ValueError('Fresh diagnostic output required')
target.parent.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(project/'tools'))
import probe_product_water as probe
from _session import load_session
os.environ.update(MCDEV_SESSION_FILE=args.session,MCDEV_OWNER=args.owner,MCDEV_ALLOW_USER_FOREGROUND='1')
session = load_session(args.session,args.owner,live=True)
assert Path(session['project']).resolve()==project
before = probe.snapshot_sources(project)
report = {'schema':1,'diagnostic_only':True,'production_qualified':False,'completed':False,
 'restored':False,'cleanup_errors':[],'captures':{},'rows':{},
 'source_contract_sha256':probe.snapshot_digest(before),'source_sha256':before,
 'session_binding':{key:session[key] for key in ('id','owner','game_pid','game_identity','session_file')},
 'host_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
with probe.base.Client(timeout=45) as client:
    check = probe.blueprints.BlueprintCheck(client,target,45.)
    installed = False
    try:
        check.run(probe.blueprints.INSTALL_PROBE)
        installed = True
        if check.navigation()['open']:
            check.run('navigator.pop()\n_result=True')
            check.wait('close prior workspace',lambda row:not row['open'] and not row['transition'],check.navigation)
        report['profile'] = check.run(probe.PROFILE%(True,True))
        check.run('owner.open_workspace()\n_result=True')
        check.wait('open pool workspace',lambda row:row['open'] and not row['transition'],check.navigation)
        for label,control in (('wet','wet'),('dry','dry'),('restored','wet')):
            row = report['rows'][label] = {'source':check.run(probe.LOAD%(('pool',control,(35.,25.,4.6)),))}
            row['ready'] = check.wait('pool '+label,
                probe.stable_scene_predicate((35.,25.,4.6),(0.,0.),probe.workspace.scene_ready),
                lambda:check.run(probe.SCENE_STATE))
            row['native'] = check.run('''rows=[]
for entry in s.liquid_controls.registry.values():
 renderer=entry.get('renderer')
 if renderer is not None:
  slot=renderer.front;actual=renderer.dolls[slot].GetModelId()
  rows.append({'cached':renderer.ids[slot],'actual':actual,
   'uniforms':dict((index,renderer.model_component.GetExtraUniformValue(actual,index))
      for index in (1,2,3,4)) if actual!=-1 else None})
_result=json.dumps(rows)''')
            time.sleep(.35)
            report['captures'][label] = probe.base.capture(args.session,args.owner,
                target.with_name(target.stem+'_'+label+'.png'),Path(args.capture_exe))
            probe.base.write(target,report)
        report['completed'] = True
    except Exception:
        report['error'] = traceback.format_exc()
    finally:
        if installed:
            for label,code in (('close','if navigator.top is not None:navigator.pop()\n_result=True'),
                               ('workspace',probe.RESTORE_PROFILE)):
                try:report[label+'_restore'] = check.run(code)
                except Exception:report['cleanup_errors'].append({'phase':label,'error':traceback.format_exc()})
        report['source_unchanged'] = before==probe.snapshot_sources(project)
        report['restored'] = not report['cleanup_errors']
        probe.base.write(target,report)
if report['completed']:
    import numpy as np
    from PIL import Image
    arrays = {key:np.asarray(Image.open(row['path']).convert('RGB')).astype(float)
              for key,row in report['captures'].items()}
    roi = (slice(354,848),slice(470,1540))
    wet,dry,restored = (arrays[key][roi] for key in ('wet','dry','restored'))
    report['pixels'] = {'roi':[470,354,1540,848],
        'wet_dry_pixels8':int(np.count_nonzero(np.max(abs(wet-dry),axis=2)>=8)),
        'restore_rgb_rmse':float(np.sqrt(np.mean((wet-restored)**2)))}
    probe.base.write(target,report)
print(json.dumps({key:report.get(key) for key in ('completed','restored','source_unchanged','pixels','error')}))
raise SystemExit(0 if report['completed'] and report['restored'] else 1)
