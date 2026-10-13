saved=getattr(sys,'_item_skeleton_r13_probe',None)
_result=True
if saved is not None and saved['nonce']=='7f41d6c1d369445a818c94af4a6e6e94' and navigator.contains(saved['key']):
 assert not navigator.is_transitioning and navigator.top.key==saved['key'],'Owned probe is not top; refuse unrelated pop'
 assert navigator.pop()
_result=True
