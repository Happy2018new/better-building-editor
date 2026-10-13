saved=getattr(sys,'_client_anchor_depth_probe',None)
_result=True
if saved is not None and saved['nonce']=='d02831073f4641b495dbc983ee45aaa0' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
