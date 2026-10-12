saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='7ee4f8762d504c39a330693190cb19e9' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
