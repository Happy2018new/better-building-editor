saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=json.dumps({'owned':False,'absent':True})
if saved is not None and saved['nonce']=='0fd836e4a53c48b1848374d8890b42be':
 actor=saved['actor']
 kind=b.factory.CreateEngineType(actor).GetEngineTypeStr() if actor is not None else None
 absent=(actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and kind is None) or (actor is None and saved['create']['state']=='returned')
 _result=json.dumps({'owned':True,'actor':actor,'kind':kind,'observed_actor_kind':saved.get('observed_actor_kind'),'absent':bool(absent),'create':saved['create']})
