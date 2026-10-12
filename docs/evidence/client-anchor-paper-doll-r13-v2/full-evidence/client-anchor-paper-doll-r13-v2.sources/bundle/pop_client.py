saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='91e00c4b19ed4ef68850a59a69f64f3d' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
