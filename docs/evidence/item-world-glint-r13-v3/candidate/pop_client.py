saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=True
if saved is not None and saved['nonce']=='f358050b20cf486da46e02bd5595da9e' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
