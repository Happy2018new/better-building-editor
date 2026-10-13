saved=sys._client_anchor_depth_probe
assert saved['nonce']=='d02831073f4641b495dbc983ee45aaa0'
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(actor).GetQueryableBoneOrientation('root',True)
_result=json.dumps({'actor':actor,'kind':kind,'bone':bone,'ready':kind is not None and bone is not None and len(bone)==4,'clock':time.time()})
