saved=getattr(sys,'_client_anchor_world_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='d06adfe2faa045968c96e1b7cdece2af' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
