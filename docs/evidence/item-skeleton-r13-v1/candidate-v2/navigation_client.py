saved=getattr(sys,'_item_skeleton_r13_probe',None)
owned=bool(saved is not None and saved['nonce']=='7f41d6c1d369445a818c94af4a6e6e94')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
