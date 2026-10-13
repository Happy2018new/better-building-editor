saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
owned=bool(saved is not None and saved['nonce']=='0fd836e4a53c48b1848374d8890b42be')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
