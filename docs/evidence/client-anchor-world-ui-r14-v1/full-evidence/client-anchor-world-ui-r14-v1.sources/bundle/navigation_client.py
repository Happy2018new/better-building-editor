saved=getattr(sys,'_client_anchor_world_ui_probe',None)
owned=bool(saved is not None and saved['nonce']=='d06adfe2faa045968c96e1b7cdece2af')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
