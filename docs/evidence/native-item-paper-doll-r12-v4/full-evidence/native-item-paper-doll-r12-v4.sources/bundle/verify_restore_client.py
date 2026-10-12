from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
saved=getattr(sys,'_native_item_ui_probe',None)
_result=True
if saved is not None and saved['nonce']=='7ee4f8762d504c39a330693190cb19e9':
 assert not navigator.is_transitioning and not navigator.contains(saved['key'])
 assert [entry.key for entry in navigator.get_entries()]==saved['navigation']
 assert s.editor.document.to_data()==saved['document']
 assert repr(_stable_palette(static_frame_item_data.FRAME_ITEMS))==saved['profiles']
 assert dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))==saved['camera']
 assert all(row['state'] in ('removed','rejected') for row in saved['attachments']),saved['attachments']
 assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
 _result=json.dumps({'attachments':saved['attachments'],'navigation':saved['navigation'],'restored':True})
 del sys._native_item_ui_probe
