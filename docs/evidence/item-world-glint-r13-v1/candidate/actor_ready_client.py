saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='0d75886eed414f05b3d0caf79fdf024c'
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
model_id=b.factory.CreateModel(actor).GetModelId()
_result=json.dumps({'actor':actor,'kind':kind,'model_id':model_id,
 'ready':kind=='modern_projection:anchor' and model_id==saved['skeleton_setup']['model_id'],'clock':time.time()})
