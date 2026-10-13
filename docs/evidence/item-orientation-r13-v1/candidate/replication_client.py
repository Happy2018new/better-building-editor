saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='bc876e0b25ac46509013814fdcf18336'
kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(saved['actor']).GetQueryableBoneOrientation('root',False)
_result=json.dumps({'actor':saved['actor'],'kind':kind,'bone':bone,'clock':time.time(),
 'ready':kind=='modern_projection:anchor' and bone is not None and len(bone)==4})
