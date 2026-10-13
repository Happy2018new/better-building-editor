from copy import deepcopy
from modern_projection.projection.bridge import _stable_palette
saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='55bcd899fd044125bde1e1d5139ade89' and not navigator.is_transitioning
label='ui_enchanted_later'
root=saved.get('root_ref')
if label!='world_empty':
 assert navigator.top is not None and navigator.top.key==saved['key'] and root and root.current
 visible=label.startswith('ui_')
 event={'operation':'owned_root_visibility:'+label,'state':'pending','attempted':True,'requested':visible}
 saved['journal'].append(event)
 event['return']=root.current.SetVisible(visible)
 event['readback']=root.current.GetVisible()
 event['state']='returned'
 assert event['readback'] is visible,event
itemcomp=b.factory.CreateItem(b.level)
assert saved['current'] is not None and saved['attachments'][-1]['item']['isEnchanted'] is True
rotation=(90.0, 0.0, 0.0)
native_item=None
if saved['current'] is not None:
 native_item={'offset':itemcomp.GetBindItemOffset(saved['actor'],saved['current'],False),
  'rotation':itemcomp.GetBindItemRotation(saved['actor'],saved['current'],False),
  'scale':itemcomp.GetBindItemScale(saved['actor'],saved['current'],False),'id':saved['current']}
 assert native_item=={'offset':(0.,0.,0.),'rotation':rotation,'scale':0.0625,'id':saved['current']},native_item
if label.startswith('ui_'):
 event={'operation':'RenderEntity:'+label,'state':'pending','attempted':True}
 saved['journal'].append(event)
 params=dict(saved['ui_params'])
 assert params['entity_id']==saved['actor']
 assert saved['skeleton_setup']['model']=='modern_projection_diagnostic_item_body_r13'
 if label in ('ui_skeleton_positive','ui_skeleton_positive_restored'):
  assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
 saved['last_submission']=params
 event['value']=saved['ref'].current.asNeteasePaperDoll().RenderEntity(params)
 event['state']='returned'
 assert event['value'] is True,event
 saved['model_read_after']=time.time()+.15
saved['control']=label
_result=json.dumps({'control':label,'actor':saved['actor'],'attachments':saved['attachments'],
 'native_item':native_item,'journal':saved['journal'],'clock':time.time()})
