saved=getattr(sys,'_native_item_ui_probe',None)
owned=bool(saved is not None and saved['nonce']=='7ee4f8762d504c39a330693190cb19e9')
_result=json.dumps({'owned':owned,'transition':bool(navigator.is_transitioning),
 'contains_owned':owned and navigator.contains(saved['key']),
 'top':navigator.top.key if navigator.top else None})
