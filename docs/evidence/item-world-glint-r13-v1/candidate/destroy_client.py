saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
if saved is None:_result=True
else:
 assert saved['nonce']=='0d75886eed414f05b3d0caf79fdf024c'
 saved['destroy_attempted']=True
 saved['destroy_returned']=True
 saved['observed_actor_kind']=saved.get('observed_actor_kind') or 'modern_projection:anchor'
 _result=json.dumps({'actor':saved['actor'],'destroy_attempted':True,'destroy_returned':True,'server_owned':True})
