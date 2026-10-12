from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
saved=getattr(sys,'_client_anchor_ui_probe',None)
_result=json.dumps({'restored':True,'owned':False})
if saved is not None and saved['nonce']=='91e00c4b19ed4ef68850a59a69f64f3d':
 assert not navigator.is_transitioning and not navigator.contains(saved['key'])
 assert [entry.key for entry in navigator.get_entries()]==saved['navigation']
 assert s.editor.document.to_data()==saved['document']
 assert repr(_stable_palette(static_frame_item_data.FRAME_ITEMS))==saved['profiles']
 assert dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))==saved['camera']
 actor=saved['actor']
 assert (actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and b.factory.CreateEngineType(actor).GetEngineTypeStr() is None) or (actor is None and saved['create']['state']=='returned'),saved['create']
 for row in saved['attachments']:
  if row['state'] not in ('removed','rejected'):row['disposed_by_owned_actor_destruction']=True
 _result=json.dumps({'restored':True,'actor_absent':True,'observed_actor_kind':saved.get('observed_actor_kind'),'attachments':saved['attachments'],'body':saved['body'],'journal':saved['journal'],'create':saved['create']})
 del sys._client_anchor_ui_probe
