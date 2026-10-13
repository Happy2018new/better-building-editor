import json,sys,time
import mod.server.extraServerApi as api
saved=getattr(sys,'_item_server_skeleton_r13_server',None)
if saved is None:_result=json.dumps({'destroyed':True,'owned':False})
else:
 assert saved['nonce']=='fd2c58cd04174a4e88235c6a5afc6b55'
 if saved['actor'] is not None and not saved.get('destroy_attempted'):
  assert saved['actor']!=saved['player'] and saved['create_state']=='returned'
  saved['destroy_attempted']=True
  saved['destroy_result']=api.GetSystem('ModernProjection','ModernProjectionServerSystem').DestroyEntity(saved['actor'])
 destroyed=saved['actor'] is None or saved.get('destroy_result') is True
 _result=json.dumps(dict(saved,destroyed=destroyed,clock=time.time()))
 if destroyed:del sys._item_server_skeleton_r13_server
