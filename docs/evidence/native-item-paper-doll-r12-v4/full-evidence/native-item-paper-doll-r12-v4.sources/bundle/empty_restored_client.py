from modern_projection.projection.bridge import _stable_palette
from copy import deepcopy
saved=sys._native_item_ui_probe
assert saved['nonce']=='7ee4f8762d504c39a330693190cb19e9' and navigator.top.key==saved['key'] and not navigator.is_transitioning
itemcomp=b.factory.CreateItem(b.level)
for row in saved['attachments']:
 if row['state']=='bound':
  row['remove_attempted']=True
  row['remove_result']=itemcomp.SetBindBoneForBindItem(saved['player'],row['id'],'',False)
  assert row['remove_result'] is True,row
  row['state']='removed'
assert all(row['state'] in ('removed','rejected') for row in saved['attachments']),saved['attachments']
label='empty_restored'
saved['control']=label
saved['current']=None
if label not in ('empty','empty_restored'):
 item=deepcopy(saved['items'][label])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','id':None,'remove_attempted':False}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(saved['player'],item,'head',False,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert row['item_nonmutation'] and valid,row
 saved['current']=identity
assert saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params']) is True
saved['model_read_after']=time.time()+.15
_result=json.dumps({'control':label,'attachments':saved['attachments'],'clock':time.time(),'ui_params':saved['ui_params']})
