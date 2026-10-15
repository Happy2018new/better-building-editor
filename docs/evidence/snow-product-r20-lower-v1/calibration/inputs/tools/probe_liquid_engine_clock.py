"""Capture an isolated clock model in an exclusively owned minimal development world."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from _session import load_session
from capture_native_burst import capture, CaptureError
from generate_liquid_engine_clock_probe import MODEL
from probe_product_water import snapshot_sources, snapshot_digest
from analyze_liquid_engine_clock import analyze_capture

SETUP = '''import sys,json
import mod.client.extraClientApi as api
assert not hasattr(sys,'_liquid_engine_clock_probe')
factory=api.GetEngineCompFactory();level=api.GetLevelId()
foot=factory.CreatePos(api.GetLocalPlayerId()).GetFootPos()
assert foot and len(foot)==3
origin=tuple(foot[i]+(6.,4.,6.)[i] for i in range(3))
center=tuple(value+2. for value in origin)
cam=factory.CreateCamera(level);model=factory.CreateModel(level)
saved={'model_id':None,'camera_position':cam.GetPosition(),'camera_rotation':cam.GetCameraRotation()}
sys._liquid_engine_clock_probe=saved
model_id=model.CreateFreeModel(%r,0)
assert model_id
saved['model_id']=model_id
assert model.SetFreeModelScale(model_id,16.,16.,16.)
assert model.SetFreeModelBoundingBox(model_id,(-4.,-4.,-4.),(4.,4.,4.))
assert model.SetFreeModelRot(model_id,0.,0.,0.)
assert model.SetFreeModelPos(model_id,*center)
payload=((64.,0.,0.,0.),(65535.,65535.,0.,0.),(0.,0.,0.,0.),(39686.,1.,16777215.,1.))
for index,value in enumerate(payload,1):assert model.SetExtraUniformValue(model_id,index,value)
target=tuple(origin[i]+(.5,1.,.5)[i] for i in range(3))
position=tuple(target[i]+(3.,5.,3.)[i] for i in range(3))
direction=api.GetRotFromDir(tuple(target[i]-position[i] for i in range(3)))
rotation=(direction[0],direction[1]+180.,0.)
cam.DepartCamera();cam.LockModCameraPitch(True);cam.LockModCameraYaw(True)
assert cam.SetCameraPos(position) and cam.SetCameraRotation(rotation)
_result=json.dumps({'model_id':model_id,'position':position,'rotation':rotation,'target':target,
 'model_center':center,'payload':payload,'source':'isolated_no_texture_clock'})
'''
STATE = '''import sys,json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory();level=api.GetLevelId();cam=factory.CreateCamera(level)
_result=json.dumps({'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),
 'screen':factory.CreateGame(level).GetScreenSize(),'model_id':sys._liquid_engine_clock_probe['model_id']})
'''
RESTORE = '''import sys,json
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory();level=api.GetLevelId()
saved=getattr(sys,'_liquid_engine_clock_probe',None)
rows=[]
if saved is not None:
 model=factory.CreateModel(level);cam=factory.CreateCamera(level)
 if saved['model_id'] is not None:
  assert model.RemoveFreeModel(saved['model_id'])
  rows.append(saved['model_id']);saved['model_id']=None
 cam.UnDepartCamera()
 del sys._liquid_engine_clock_probe
_result=json.dumps({'removed':rows,'camera_bound_to_player':True})
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--burst-exe', type=Path, required=True)
    parser.add_argument('--burst-sha256', required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose fresh clock evidence')
    os.environ.update(MCDEV_SESSION_FILE=str(Path(args.session).resolve(strict=True)), MCDEV_OWNER=args.owner)
    session = load_session(args.session, args.owner, live=True)
    if Path(session['project']).resolve() != ROOT:
        parser.error('Use an exclusively owned session bound to this project')
    before = snapshot_sources(ROOT)
    report = {'schema_version': 1, 'completed': False, 'restored': False,
              'source_unchanged': False, 'cleanup_errors': [], 'product_acceptance_claimed': False,
              'source_contract_sha256': snapshot_digest(before), 'source_sha256': before}

    def save():
        args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='ascii')

    with Client(timeout=30) as client:
        def run(code):
            value = return_value(client.call('execute_code', {'code': code, 'is_client': True, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value

        attempted = False
        try:
            attempted = True
            report['setup'] = run(SETUP % MODEL)
            time.sleep(.4)
            report['camera_before'] = run(STATE)
            report['capture'] = capture(args.session, args.owner, args.output.with_suffix(''),
                                        args.burst_exe, args.burst_sha256, duration_ms=1200,
                                        max_frames=240, max_gap_ms=150)
            report['camera_after'] = run(STATE)
            if report['camera_before'] != report['camera_after']:
                raise RuntimeError('Independent native clock camera changed')
            report['clock'] = analyze_capture(report['capture'])
            report['completed'] = report['clock']['passed']
        except CaptureError as error:
            report['capture'] = error.report
            report['error'] = str(error)
        except Exception as error:
            report['error'] = type(error).__name__ + ': ' + str(error)
        finally:
            if attempted:
                try:
                    report['restore'] = run(RESTORE)
                    report['restored'] = True
                except Exception as error:
                    report['cleanup_errors'].append(type(error).__name__ + ': ' + str(error))
            report['source_unchanged'] = snapshot_sources(ROOT) == before
            save()
    print(json.dumps({key: report.get(key) for key in ('completed', 'restored', 'source_unchanged', 'error')}))
    return 0 if report['completed'] and report['restored'] and report['source_unchanged'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
