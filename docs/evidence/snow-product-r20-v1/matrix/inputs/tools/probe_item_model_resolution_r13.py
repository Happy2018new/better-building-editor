"""Bounded same-session model resolution; no UI, screenshots or item bindings."""
import json
import os
from pathlib import Path
import sys
import time

from isolated_diagnostic_module import load

route=load('item_skeleton_owner_r13')

shared=route.shared
PREFIX='item-model-resolution-r13-v1'
ATTRIBUTE='_item_model_resolution_r13'
PREPARE="""import json,os,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
b=owner.bridge
assert not hasattr(sys,'%s') and not hasattr(sys,'%s')
assert not navigator.get_entries() and not navigator.is_transitioning
assert b.session.ready and not b.session.busy and not b.session.projection_active
player=api.GetLocalPlayerId()
foot=b.factory.CreatePos(player).GetFootPos()
saved={'actor':None,'models':[],'journal':[],'cleanup_errors':[],'player':player,'foot':foot,'created_clock':time.time()}
sys.%s=saved
saved['actor']=b.system.CreateClientEntityByTypeStr('modern_projection:anchor',(foot[0]+2.,foot[1]+1.,foot[2]+2.),(0.,0.))
assert saved['actor'] and saved['actor']!=player
_result=json.dumps({'actor':saved['actor'],'created_clock':saved['created_clock'],'pid':os.getpid(),'token':getattr(sys,'_pyreact_mcdk_session',None)})
""" % (ATTRIBUTE,route.candidate.ATTRIBUTE,ATTRIBUTE)
READY="""import json,time,sys
import mod.client.extraClientApi as api
b=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
saved=sys.%s
kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr()
bone=b.factory.CreateActorRender(saved['actor']).GetQueryableBoneOrientation('root',True)
_result=json.dumps({'actor':saved['actor'],'kind':kind,'bone':bone,'clock':time.time(),
 'ready':kind=='modern_projection:anchor' and bone is not None and len(bone)==4})
""" % ATTRIBUTE
RESOLVE="""import json,time,sys
import mod.client.extraClientApi as api
b=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
saved=sys.%s
name=%r
level=b.factory.CreateModel(b.level)
event={'model':name,'operation':'CreateFreeModel','state':'pending','clock':time.time()}
saved['journal'].append(event)
identity=level.CreateFreeModel(name)
event.update(state='returned',model_id=identity)
if isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>0:
 saved['models'].append({'id':identity,'model':name,'removed':False})
 event['texture']=level.GetTexture(identity)
 event['material']=level.GetModelMaterial(identity)
event={'model':name,'operation':'SetModel','state':'pending','clock':time.time(),'actor':saved['actor']}
saved['journal'].append(event)
identity=b.factory.CreateModel(saved['actor']).SetModel(name)
event.update(state='returned',model_id=identity)
_result=json.dumps({'journal':saved['journal'],'models':saved['models'],'actor':saved['actor'],'clock':time.time()})
"""
CLEANUP="""import json,time,sys
import mod.client.extraClientApi as api
b=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
saved=getattr(sys,'%s',None)
if saved is None:
 _result=json.dumps({'restored':True,'owned':False})
else:
 model=b.factory.CreateModel(b.level)
 for row in saved['models']:
  if not row.get('remove_attempted'):
   row['remove_attempted']=True
   try:
    row['remove_result']=model.RemoveFreeModel(row['id'])
    row['removed']=row['remove_result'] is True
    if not row['removed']:saved['cleanup_errors'].append('Free model removal failed: '+repr(row))
   except Exception as error:saved['cleanup_errors'].append(repr(error))
 if saved['actor'] and not saved.get('destroy_attempted'):
  saved['destroy_attempted']=True
  try:
   b.system.DestroyClientEntity(saved['actor'])
   saved['destroy_returned']=True
  except Exception as error:saved['cleanup_errors'].append(repr(error))
 _result=json.dumps({'cleanup_errors':saved['cleanup_errors'],'models':saved['models'],
  'journal':saved['journal'],'actor':saved['actor'],'destroy_returned':saved.get('destroy_returned',False)})
""" % ATTRIBUTE
VERIFY="""import json,time,sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
b=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
saved=getattr(sys,'%s',None)
if saved is None:_result=json.dumps({'restored':True,'owned':False})
else:
 kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr() if saved['actor'] else None
 foot=b.factory.CreatePos(saved['player']).GetFootPos()
 restored=kind is None and not saved['cleanup_errors'] and all(row['removed'] for row in saved['models'])
 assert not navigator.get_entries() and not navigator.is_transitioning
 assert all(abs(a-v)<.0001 for a,v in zip(foot,saved['foot']))
 _result=json.dumps({'restored':restored,'actor_absent':kind is None,'journal':saved['journal'],'models':saved['models'],'clock':time.time()})
 if restored:del sys.%s
""" % (ATTRIBUTE,ATTRIBUTE)


def main():
    route.configure()
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','execute'))
    parser.add_argument('bundle')
    parser.add_argument('--session-file')
    args=parser.parse_args()
    if args.command=='prepare':
        plan=shared.prepare(args.bundle)
        print(json.dumps({'owner_plan_sha256':shared.digest(Path(args.bundle)/'plan.json'),'sources':len(plan['source_pins'])}))
        return
    plan=shared.verify(args.bundle)
    session=Path(args.session_file).resolve(strict=True)
    guard=route.SkeletonOwnerGuard(session,plan)
    output=shared.artifact_directory(session)/(PREFIX+'.json')
    shared.require(not output.exists(),'Preserve earlier resolution diagnostic')
    started=time.monotonic()
    report={'schema':1,'started_at':shared.timestamp(),'normal_seconds':30,'cleanup_seconds':45,'outer_seconds':60,
            'session_file':str(session),'owner':shared.OWNER,'owner_plan_sha256':shared.digest(Path(args.bundle)/'plan.json'),
            'requests':[],'network_requests':[],'errors':[],'cleanup_errors':[],'completed':False,'restored':False,
            'no_ui_mount':True,'no_screenshots':True,'no_items_bound':True,'production_rendering_accepted':False}
    preserve=lambda:shared.save(output,report)
    client=None
    try:
        os.environ.update(MCDEV_SESSION_FILE=str(session),MCDEV_OWNER=shared.OWNER)
        client=shared.recorded_client(guard,report,preserve,started+30.,started+60.)
        client.__enter__()
        report['prepare']=shared.execute(client,PREPARE)
        shared.validate_identity(report['prepare'],client)
        while time.monotonic()<started+15.:
            row=shared.execute(client,READY)
            report.setdefault('readiness',[]).append(row)
            preserve()
            if row['ready']:
                break
            time.sleep(.2)
        else:raise TimeoutError('Owned anchor root never initialized')
        report['observations']=[]
        for name in (route.candidate.MODEL,'ceshi_body'):
            report['observations'].append(shared.execute(client,RESOLVE % (ATTRIBUTE,name)))
            preserve()
        report['completed']=True
    except Exception as error:
        report['errors'].append(repr(error))
    finally:
        if client is not None:
            client.frame_dispatch_deadline=started+45.
            try:
                report['cleanup']=shared.execute(client,CLEANUP)
                report['cleanup_errors'].extend(report['cleanup'].get('cleanup_errors',[]))
                while time.monotonic()<started+45.:
                    report['verify']=shared.execute(client,VERIFY)
                    preserve()
                    if report['verify']['restored']:
                        report['restored']=True
                        break
                    time.sleep(.2)
            except Exception as error:report['cleanup_errors'].append(repr(error))
            try:client.close()
            except Exception as error:report['cleanup_errors'].append('close: '+repr(error))
        try:
            guard.verify_after()
            report['protected_sources_unchanged']=True
        except Exception as error:report['cleanup_errors'].append('source verify: '+repr(error))
        report['restored']=report['restored'] and not report['cleanup_errors']
        report.update(finished_at=shared.timestamp(),elapsed_seconds=time.monotonic()-started)
        preserve()
    print(json.dumps({k:report[k] for k in ('completed','restored','errors','cleanup_errors','elapsed_seconds')}))


if __name__=='__main__':
    main()
