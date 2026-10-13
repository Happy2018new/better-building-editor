saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='bc876e0b25ac46509013814fdcf18336' and saved['actor'] is None
approved=APPROVED_ACTOR_PAYLOAD
assert approved['nonce']==saved['nonce'] and approved['position']==list(saved['position'])
saved['actor']=approved['actor']
saved['create'].update(state='returned',value=approved['actor'])
assert isinstance(saved['actor'],basestring) and saved['actor'] not in ('', '-1', saved['player'])
saved['ui_params']['entity_id']=saved['actor']
_result=json.dumps({'actor':saved['actor'],'nonce':saved['nonce']})
