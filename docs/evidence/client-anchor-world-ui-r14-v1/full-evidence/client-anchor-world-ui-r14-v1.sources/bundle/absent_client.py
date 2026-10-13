saved=getattr(sys,'_client_anchor_world_ui_probe',None)
_result=json.dumps({'owned':False,'absent':True})
if saved is not None and saved['nonce']=='d06adfe2faa045968c96e1b7cdece2af':
 actor=saved['actor']
 kind=b.factory.CreateEngineType(actor).GetEngineTypeStr() if actor is not None else None
 absent=(actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and kind is None) or (actor is None and saved['create']['state']=='returned')
 _result=json.dumps({'owned':True,'actor':actor,'kind':kind,'observed_actor_kind':saved.get('observed_actor_kind'),'absent':bool(absent),'create':saved['create']})
