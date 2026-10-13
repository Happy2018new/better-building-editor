saved=getattr(sys,'_client_anchor_world_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='d06adfe2faa045968c96e1b7cdece2af':
 actor=saved['actor']
 if actor is not None:
  assert actor!=saved['player'] and saved['create'].get('value')==actor
  assert not saved.get('destroy_attempted'),'Do not retry uncertain actor destruction'
  try:
   saved['pre_destroy_kind']=b.factory.CreateEngineType(actor).GetEngineTypeStr()
   if saved['pre_destroy_kind'] is not None:saved['observed_actor_kind']=saved['pre_destroy_kind']
  except Exception as error:saved['pre_destroy_kind_error']=repr(error)
  saved['destroy_attempted']=True
  saved['destroy_result']=b.system.DestroyClientEntity(actor)
  saved['destroy_returned']=True
 _result=json.dumps({'actor':actor,'create':saved['create'],'observed_actor_kind':saved.get('observed_actor_kind'),'pre_destroy_kind':saved.get('pre_destroy_kind'),'pre_destroy_kind_error':saved.get('pre_destroy_kind_error'),'destroy_attempted':saved.get('destroy_attempted',False),'destroy_returned':saved.get('destroy_returned',False)})
