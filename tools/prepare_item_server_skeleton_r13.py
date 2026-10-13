"""Prepare the server-owned variant; every actor and item ID stays separately owned."""
import ast
import json
from pathlib import Path

import prepare_item_skeleton_candidate_r13 as client_route

ROOT=client_route.ROOT
MODEL=client_route.MODEL
ATTRIBUTE='_item_server_skeleton_r13_probe'
SERVER_ATTRIBUTE='_item_server_skeleton_r13_server'
POSITIVE_STATES=client_route.POSITIVE_STATES
POSITIVE_NAME=client_route.POSITIVE_NAME
POSITIVE_TARGET='owned_server_skeleton_actor'
STATES=client_route.STATES
UI=client_route.UI
digest=client_route.digest
archived_files=client_route.archived_files
resources=client_route.resources
EXACT_PLAN_SHA256=None


def snippets(nonce):
    programs={name:source.replace(client_route.ATTRIBUTE,ATTRIBUTE)
              for name,source in client_route.snippets(nonce).items()}
    install=programs['install_client.py']
    begin=install.index("candidate=b.system.CreateClientEntityByTypeStr(")
    end=install.index("_result=json.dumps(dict((key,saved[key])",begin)
    replacement="""saved['skeleton_setup']={'model':%r,'model_id':None,'state':'pending'}
""" % MODEL
    programs['install_client.py']=install[:begin]+replacement+install[end:]
    for name in STATES:
        source=programs[name+'_client.py']
        source=source.replace("'root',True,(0.,0.,0.),(0.,0.,0.),1.)", "'root',False,(0.,0.,0.),(0.,0.,0.),1.)")
        source=source.replace("row['id'],'',True)","row['id'],'',False)")
        source=source.replace("saved['current'],True)","saved['current'],False)")
        programs[name+'_client.py']=source
    programs['remove_client.py']=programs['remove_client.py'].replace("row['id'],'',True)","row['id'],'',False)")
    programs['destroy_client.py']="""saved=getattr(sys,%r,None)
if saved is None:_result=True
else:
 assert saved['nonce']==%r
 saved['destroy_attempted']=True
 saved['destroy_returned']=True
 saved['observed_actor_kind']=saved.get('observed_actor_kind') or 'modern_projection:anchor'
 _result=json.dumps({'actor':saved['actor'],'destroy_attempted':True,'destroy_returned':True,'server_owned':True})
""" % (ATTRIBUTE,nonce)
    programs['adopt_client.py']="""saved=sys.%s
assert saved['nonce']==%r and saved['actor'] is None
approved=APPROVED_ACTOR_PAYLOAD
assert approved['nonce']==saved['nonce'] and approved['position']==list(saved['position'])
saved['actor']=approved['actor']
saved['create'].update(state='returned',value=approved['actor'])
assert isinstance(saved['actor'],basestring) and saved['actor'] not in ('', '-1', saved['player'])
saved['ui_params']['entity_id']=saved['actor']
_result=json.dumps({'actor':saved['actor'],'nonce':saved['nonce']})
""" % (ATTRIBUTE,nonce)
    programs['replication_client.py']="""saved=sys.%s
assert saved['nonce']==%r
kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(saved['actor']).GetQueryableBoneOrientation('root',False)
_result=json.dumps({'actor':saved['actor'],'kind':kind,'bone':bone,'clock':time.time(),
 'ready':kind=='modern_projection:anchor' and bone is not None and len(bone)==4})
""" % (ATTRIBUTE,nonce)
    programs['set_model_client.py']="""saved=sys.%s
assert saved['nonce']==%r
saved['skeleton_setup']['model_id']=b.factory.CreateModel(saved['actor']).SetModel(%r)
saved['skeleton_setup']['state']='returned'
identity=saved['skeleton_setup']['model_id']
assert isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0,saved['skeleton_setup']
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','foot','position','actor','create',
 'navigation','document','profiles','camera','declared_size','size_inputs','ui_params','native_camera','empty_cells',
 'roi_receipt','skeleton_setup')))
""" % (ATTRIBUTE,nonce,MODEL)
    programs['create_server.py']="""import json,sys,time
import mod.server.extraServerApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionServerSystem')
assert owner is not None and not hasattr(sys,%r)
approved=APPROVED_CLIENT_PAYLOAD
assert approved['nonce']==%r and approved['player'] in api.GetPlayerList()
factory=api.GetEngineCompFactory()
dimension=factory.CreateDimension(approved['player']).GetEntityDimensionId()
assert dimension==0
saved={'nonce':approved['nonce'],'position':approved['position'],'player':approved['player'],
 'actor':None,'dimension':dimension,'create_state':'pending','created_clock':time.time()}
sys.%s=saved
saved['actor']=owner.CreateEngineEntityByTypeStr('modern_projection:anchor',tuple(approved['position']),
 (0.,0.),dimension,True,False)
saved['create_state']='returned'
_result=json.dumps(saved)
""" % (SERVER_ATTRIBUTE,nonce,SERVER_ATTRIBUTE)
    programs['destroy_server.py']="""import json,sys,time
import mod.server.extraServerApi as api
saved=getattr(sys,%r,None)
if saved is None:_result=json.dumps({'destroyed':True,'owned':False})
else:
 assert saved['nonce']==%r
 if saved['actor'] is not None and not saved.get('destroy_attempted'):
  assert saved['actor']!=saved['player'] and saved['create_state']=='returned'
  saved['destroy_attempted']=True
  saved['destroy_result']=api.GetSystem('ModernProjection','ModernProjectionServerSystem').DestroyEntity(saved['actor'])
 destroyed=saved['actor'] is None or saved.get('destroy_result') is True
 _result=json.dumps(dict(saved,destroyed=destroyed,clock=time.time()))
 if destroyed:del sys.%s
""" % (SERVER_ATTRIBUTE,nonce,SERVER_ATTRIBUTE)
    for name,source in programs.items():
        ast.parse(source,filename=name)
    return programs


def contract():
    value=client_route.contract()
    value.update(candidate='same_server_owned_actor_opaque_skeleton_ordinary_item',
                 is_client_entity=False,server_actor_count=1,server_actor_is_npc=True,
                 replicated_kind_and_root_before_set_model=True,
                 source_sha256=digest(Path(__file__).read_bytes()),
                 client_generator_sha256=digest(Path(client_route.__file__).read_bytes()))
    return value


def prepare(output):
    return client_route.prepare(output,snippets,contract,__file__)


def verify(bundle):
    return client_route.verify(bundle,snippets,contract,__file__)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','verify'))
    parser.add_argument('path')
    args=parser.parse_args()
    result=prepare(args.path) if args.command=='prepare' else verify(args.path)
    print(json.dumps({'files':len(result['files']),'candidate_sha256':digest((Path(args.path)/'plan.json').read_bytes()),
                      'sdk_dispatch_attempted':False}))
