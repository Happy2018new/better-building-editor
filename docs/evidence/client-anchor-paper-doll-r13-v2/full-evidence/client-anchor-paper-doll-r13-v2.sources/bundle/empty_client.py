from copy import deepcopy
from modern_projection.projection.bridge import _stable_palette,_native_palette
saved=sys._client_anchor_ui_probe
assert saved['nonce']=='91e00c4b19ed4ef68850a59a69f64f3d' and navigator.top.key==saved['key'] and not navigator.is_transitioning
actor=saved['actor']
label='empty'
itemcomp=b.factory.CreateItem(b.level)
render=b.factory.CreateActorRender(actor)
def mutation(operation,call):
 row={'operation':operation,'state':'pending','attempted':True}
 saved['journal'].append(row)
 value=call()
 row.update(state='returned',value=value)
 assert value is True,row
 return value
def remove_item():
 for row in saved['attachments']:
  if row['state']=='bound':
   assert not row.get('remove_attempted'),row
   row['remove_attempted']=True
   row['remove_result']=itemcomp.SetBindBoneForBindItem(actor,row['id'],'',True)
   assert row['remove_result'] is True,row
   row['state']='removed'
 saved['current']=None
def bind_item():
 assert saved['current'] is None and all(row['state']=='removed' for row in saved['attachments'])
 item=deepcopy(saved['plain'])
 row={'control':label,'item':deepcopy(item),'canonical':repr(_stable_palette(item)),
  'state':'pending','attempted':True,'id':None,'offset':[0.,0.,0.],'rotation':[0.,0.,0.],'scale':1.}
 saved['attachments'].append(row)
 identity=itemcomp.BindItemToMinecraftModel(actor,item,'root',True,(0.,0.,0.),(0.,0.,0.),1.)
 row['id']=identity
 row['item_nonmutation']=repr(_stable_palette(item))==row['canonical']
 valid=isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
 row['state']='rejected' if identity==-1 else 'bound' if valid else 'pending'
 assert valid and row['item_nonmutation'],row
 saved['current']=identity
if label in ('plain','combined_minus','combined_plus'):bind_item()
elif label in ('body_only_minus','body_only_plus','empty_restored'):remove_item()
if label=='body_only_minus':
 assert saved['body'] is None
 body=saved['body']={'name':'client_anchor_body_'+saved['nonce'],'state':'pending','combine_attempted':False,'add_attempted':False}
 data=_native_palette({'volume': (1, 3, 3), 'common': {('minecraft:stone', 0): [0, 1, 2, 3, 4, 5, 6, 7, 8]}, 'extra': {}, 'states': {}, 'extraStates': {}, 'actor': {}, 'void': False, 'eliminateAir': True})
 palette=b.factory.CreateBlock(b.level).GetBlankBlockPalette()
 assert palette is not None
 mutation('DeserializeBlockPalette',lambda:palette.DeserializeBlockPalette(data))
 body['palette_before']=repr(_stable_palette(palette.SerializeBlockPalette()))
 body['combine_attempted']=True
 body['model']=b.factory.CreateBlockGeometry(b.level).CombineBlockPaletteToGeometry(palette,body['name'],0)
 body['palette_nonmutation']=body['palette_before']==repr(_stable_palette(palette.SerializeBlockPalette()))
 assert body['model'] in (body['name'],body['name'].encode('utf8')) and body['palette_nonmutation'],body
 body['add_attempted']=True
 mutation('AddActorBlockGeometry',lambda:render.AddActorBlockGeometry(body['model'],(0.,0.,-2.),(0.,0.,0.)))
 body.update(state='attached',offset=[0.,0.,-2.],rotation=[0.,0.,0.],visible=True)
elif label=='body_only_plus':
 body=saved['body']
 assert body and body['state']=='attached'
 body['requested_offset']=[0.,0.,2.]
 mutation('SetActorBlockGeometryOffset',lambda:render.SetActorBlockGeometryOffset(body['model'],(0.,0.,2.)))
 body['offset']=[0.,0.,2.]
elif label=='plain_restored':
 body=saved['body']
 assert saved['current'] is not None and body and body['state']=='attached'
 body['requested_visible']=False
 mutation('SetActorBlockGeometryVisible',lambda:render.SetActorBlockGeometryVisible(body['model'],False))
 body['visible']=False
saved['control']=label
mutation('RenderEntity:'+label,lambda:saved['ref'].current.asNeteasePaperDoll().RenderEntity(saved['ui_params']))
saved['model_read_after']=time.time()+.15
native_item=None
if saved['current'] is not None:
 native_item={'offset':itemcomp.GetBindItemOffset(actor,saved['current'],True),
  'rotation':itemcomp.GetBindItemRotation(actor,saved['current'],True),
  'scale':itemcomp.GetBindItemScale(actor,saved['current'],True)}
 assert native_item=={'offset':(0.,0.,0.),'rotation':(0.,0.,0.),'scale':1.},native_item
_result=json.dumps({'control':label,'actor':actor,'attachments':saved['attachments'],'body':saved['body'],
 'journal':saved['journal'],'native_item':native_item,'clock':time.time(),'ui_params':saved['ui_params']})
