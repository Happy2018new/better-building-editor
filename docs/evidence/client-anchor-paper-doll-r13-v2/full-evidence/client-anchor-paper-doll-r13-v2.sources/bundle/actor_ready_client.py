saved=sys._client_anchor_ui_probe
assert saved['nonce']=='91e00c4b19ed4ef68850a59a69f64f3d'
actor=saved['actor']
kind=b.factory.CreateEngineType(actor).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
bone=b.factory.CreateActorRender(actor).GetQueryableBoneOrientation('root',True)
_result=json.dumps({'actor':actor,'kind':kind,'bone':bone,'ready':kind is not None and bone is not None and len(bone)==4,'clock':time.time()})
