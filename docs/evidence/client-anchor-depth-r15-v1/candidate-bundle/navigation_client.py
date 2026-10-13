saved=getattr(sys,'_client_anchor_depth_probe',None)
owned=bool(saved is not None and saved['nonce']=='d02831073f4641b495dbc983ee45aaa0')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
