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
saved=sys._item_server_skeleton_r13_probe
assert saved['nonce']=='bc876e0b25ac46509013814fdcf18336'
ref=saved.get('ref')
root_ref=saved.get('root_ref')
ready=bool(navigator.top and navigator.top.key==saved['key'] and not navigator.is_transitioning and ref and ref.current and root_ref and root_ref.current and len(saved.get('marker_refs',[]))==4 and all(marker.current for marker in saved['marker_refs']))
model=None
native_layout=None
now=time.time()
if ready:
 host=api.GetTopScreen()
 assert host is not None and host is navigator.top._host
 viewport=host.GetBaseUIControl(host._root_path)
 assert viewport is not None
 def native_rect(control):
  position=control.GetGlobalPosition()
  size=control.GetSize()
  return {'x':position[0],'y':position[1],'width':size[0],'height':size[1],'path':control.GetPath()}
 game=b.factory.CreateGame(b.level)
 native_layout={'paper_doll':native_rect(ref.current),'root':native_rect(root_ref.current),
  'viewport':native_rect(viewport),'screen_size_api_observed':game.GetScreenSize(),
  'screen_view_api_observed':game.GetScreenViewInfo(),
  'markers':[dict(marker,rect=native_rect(saved['marker_refs'][index].current)) for index,marker in enumerate(saved['markers'])],
  'declared_size':saved['declared_size'],'size_inputs':saved['size_inputs']}
 if saved.get('ready_first_seen') is None:saved['ready_first_seen']=now
 if now>=max(saved['ready_first_seen']+.15,saved.get('model_read_after',0.)):
  model=ref.current.asNeteasePaperDoll().GetModelId()
else:saved['ready_first_seen']=None
_result=json.dumps({'ready':ready,'control':saved['control'],'model_id':model,'clock':now,
 'native_layout':native_layout,
 'model_read_deferred':ready and model is None,
 'actor':saved['actor'],'journal':saved['journal'],'body':saved['body'],
 'version':api.GetMinecraftVersion(),'attachments':saved['attachments'],'ui_params':saved['ui_params']})
row=json.loads(_result)
root=saved.get('root_ref')
visible=root.current.GetVisible() if root and root.current else None
kind=b.factory.CreateEngineType(saved['actor']).GetEngineTypeStr()
if kind is not None:saved['observed_actor_kind']=kind
actual=native_camera_snapshot()
foot=b.factory.CreatePos(saved['player']).GetFootPos()
camera_matches=native_camera_matches(actual,saved['native_camera'])
foot_matches=foot is not None and len(foot)==3 and all(abs(v-a)<=.0001 for v,a in zip(foot,saved['foot']))
if saved['control'].startswith('world_'):
 row['ready']=kind=='modern_projection:anchor' and visible in (None,False) and not navigator.is_transitioning
else:row['ready']=row['ready'] and visible is True
row.update(root_visible=visible,actor_kind=kind,native_camera=actual,camera_matches=camera_matches,
 player_foot=foot,player_foot_matches=foot_matches,roi_receipt=saved['roi_receipt'])
_result=json.dumps(row)
row=json.loads(_result)
row['last_submission']=saved.get('last_submission')
_result=json.dumps(row)
row=json.loads(_result)
identity=row['model_id']
row['skeleton_setup']=saved['skeleton_setup']
row['ready']=row['ready'] and isinstance(identity,(int,long)) and not isinstance(identity,bool) and identity>=0
_result=json.dumps(row)
