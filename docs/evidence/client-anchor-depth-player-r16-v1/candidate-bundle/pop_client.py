saved=getattr(sys,'_client_anchor_depth_probe',None)
_result=True
if saved is not None and saved['nonce']=='6a932b71eb8e466e82468788bb23e66e' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
