saved=getattr(sys,'_client_anchor_depth_probe',None)
owned=bool(saved is not None and saved['nonce']=='6a932b71eb8e466e82468788bb23e66e')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
