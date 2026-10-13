from copy import deepcopy
from modern_projection.projection.bridge import _stable_palette
saved=sys._client_anchor_depth_probe
assert saved['nonce']=='6a932b71eb8e466e82468788bb23e66e' and not navigator.is_transitioning
label='ui_empty_restored'
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
if label=='ui_plain_depth15':
 assert not saved['attachments'] and saved['current'] is None
 item=deepcopy(saved['plain'])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','attempted':True,'id':None,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(saved['actor'],item,'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert valid and row['item_nonmutation'],row
 saved['current']=identity
elif label=='ui_empty_restored':
 assert len(saved['attachments'])==1 and saved['attachments'][0]['state']=='bound'
 row=saved['attachments'][0]
 assert not row.get('remove_attempted'),row
 row['remove_attempted']=True
 row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['actor'],row['id'],'',True)
 assert row['remove_result'] is True,row
 row['state']='removed'
 saved['current']=None
if label in ('ui_plain_depth15','ui_plain_depth50','ui_plain_depth15_repeat'):
 assert len(saved['attachments'])==1 and saved['attachments'][0]['state']=='bound'
native_item=None
if saved['current'] is not None:
 native_item={'offset':itemcomp.GetBindItemOffset(saved['actor'],saved['current'],True),
  'rotation':itemcomp.GetBindItemRotation(saved['actor'],saved['current'],True),
  'scale':itemcomp.GetBindItemScale(saved['actor'],saved['current'],True),'id':saved['current']}
 assert native_item=={'offset':(0.,0.,0.),'rotation':(0.,0.,0.),'scale':1.,'id':saved['current']},native_item
if label.startswith('ui_'):
 event={'operation':'RenderEntity:'+label,'state':'pending','attempted':True}
 saved['journal'].append(event)
 params=dict(saved['ui_params'])
 params['render_depth']=-50 if label=='ui_plain_depth50' else -15
 if label in ('ui_player_positive','ui_player_positive_restored'):
  assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
  params['entity_id']=saved['player']
  params['scale']=1.
  params['render_depth']=-50
  params['init_rot_y']=60.
 saved['last_submission']=params
 event['value']=saved['ref'].current.asNeteasePaperDoll().RenderEntity(params)
 event['state']='returned'
 assert event['value'] is True,event
 saved['model_read_after']=time.time()+.15
saved['control']=label
_result=json.dumps({'control':label,'actor':saved['actor'],'attachments':saved['attachments'],
 'native_item':native_item,'journal':saved['journal'],'clock':time.time()})
