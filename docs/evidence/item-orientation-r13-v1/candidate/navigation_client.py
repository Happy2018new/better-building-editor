saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
owned=bool(saved is not None and saved['nonce']=='bc876e0b25ac46509013814fdcf18336')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
