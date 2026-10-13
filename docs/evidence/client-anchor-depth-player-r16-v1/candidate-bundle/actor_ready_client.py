saved=sys._client_anchor_depth_probe
assert saved['nonce']=='6a932b71eb8e466e82468788bb23e66e'
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(actor).GetQueryableBoneOrientation('root',True)
_result=json.dumps({'actor':actor,'kind':kind,'bone':bone,'ready':kind is not None and bone is not None and len(bone)==4,'clock':time.time()})
