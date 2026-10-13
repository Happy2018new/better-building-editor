saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='6a73798d9ff44f93b1b9a2ca624820ef'
saved['skeleton_setup']['model_id']=b.factory.CreateModel(saved['actor']).SetModel('modern_projection_diagnostic_item_body_r13')
saved['skeleton_setup']['state']='returned'
identity=saved['skeleton_setup']['model_id']
assert isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0,saved['skeleton_setup']
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','foot','position','actor','create',
 'navigation','document','profiles','camera','declared_size','size_inputs','ui_params','native_camera','empty_cells',
 'roi_receipt','skeleton_setup')))
