def native_camera_snapshot():
 cam=b.factory.CreateCamera(b.level)
 return {'position':cam.GetPosition(),'rotation':cam.GetCameraRotation(),'forward':cam.GetForward(),
  'pitch_lock':cam.IsModCameraLockPitch(),'yaw_lock':cam.IsModCameraLockYaw(),
  'motions':cam.GetCameraMotions()}
def native_camera_matches(actual,expected):
 return (all(abs(a-v)<=.01 for a,v in zip(actual['position'],expected['position'])) and
  all(abs((a-v+180.)%360.-180.)<=.01 for a,v in zip(actual['rotation'],expected['rotation'])) and
  all(abs(a-v)<=.0001 for a,v in zip(actual['forward'],expected['forward'])) and
  all(actual[key]==expected[key] for key in ('pitch_lock','yaw_lock','motions')))
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
saved=getattr(sys,'_item_server_skeleton_r13_probe',None)
_result=json.dumps({'restored':True,'owned':False})
if saved is not None and saved['nonce']=='0d75886eed414f05b3d0caf79fdf024c':
 assert not navigator.is_transitioning and not navigator.contains(saved['key'])
 assert [entry.key for entry in navigator.get_entries()]==saved['navigation']
 assert s.editor.document.to_data()==saved['document']
 assert repr(_stable_palette(static_frame_item_data.FRAME_ITEMS))==saved['profiles']
 assert dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))==saved['camera']
 actual=native_camera_snapshot()
 foot=b.factory.CreatePos(saved['player']).GetFootPos()
 assert native_camera_matches(actual,saved['native_camera']),('Native camera changed',actual,saved['native_camera'])
 assert foot is not None and len(foot)==3 and all(abs(v-a)<=.0001 for v,a in zip(foot,saved['foot'])),('Player foot changed',foot,saved['foot'])
 actor=saved['actor']
 assert (actor is not None and saved.get('observed_actor_kind') is not None and saved.get('destroy_attempted') and b.factory.CreateEngineType(actor).GetEngineTypeStr() is None) or (actor is None and saved['create']['state']=='returned'),saved['create']
 for row in saved['attachments']:
  if row['state'] not in ('removed','rejected'):row['disposed_by_owned_actor_destruction']=True
 _result=json.dumps({'restored':True,'actor_absent':True,'observed_actor_kind':saved.get('observed_actor_kind'),'attachments':saved['attachments'],'body':saved['body'],'journal':saved['journal'],'create':saved['create']})
 del sys._item_server_skeleton_r13_probe
