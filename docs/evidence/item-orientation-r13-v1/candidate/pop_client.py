saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=True
if saved is not None and saved['nonce']=='bc876e0b25ac46509013814fdcf18336' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
