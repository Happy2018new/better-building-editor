saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=json.dumps({'owned':False,'absent':True})
if saved is not None and saved['nonce']=='fd2c58cd04174a4e88235c6a5afc6b55':
 actor=saved['actor']
 kind=b.factory.CreateEngineType(actor).GetEngineTypeStr() if actor is not None else None
 absent=(actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and kind is None) or (actor is None and saved['create']['state']=='returned')
 _result=json.dumps({'owned':True,'actor':actor,'kind':kind,'observed_actor_kind':saved.get('observed_actor_kind'),'absent':bool(absent),'create':saved['create']})
