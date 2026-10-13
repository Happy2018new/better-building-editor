saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=True
if saved is not None and saved['nonce']=='0fd836e4a53c48b1848374d8890b42be' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
