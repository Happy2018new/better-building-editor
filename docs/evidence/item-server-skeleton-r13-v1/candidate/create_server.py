import json,sys,time
import mod.server.extraServerApi as api
owner=api.GetSystem('ModernProjection','ModernProjectionServerSystem')
assert owner is not None and not hasattr(sys,'_item_server_skeleton_r13_server')
approved=APPROVED_CLIENT_PAYLOAD
assert approved['nonce']=='fd2c58cd04174a4e88235c6a5afc6b55' and approved['player'] in api.GetPlayerList()
factory=api.GetEngineCompFactory()
dimension=factory.CreateDimension(approved['player']).GetEntityDimensionId()
assert dimension==0
saved={'nonce':approved['nonce'],'position':approved['position'],'player':approved['player'],
 'actor':None,'dimension':dimension,'create_state':'pending','created_clock':time.time()}
sys._item_server_skeleton_r13_server=saved
saved['actor']=owner.CreateEngineEntityByTypeStr('modern_projection:anchor',tuple(approved['position']),
 (0.,0.),dimension,True,False)
saved['create_state']='returned'
_result=json.dumps(saved)
