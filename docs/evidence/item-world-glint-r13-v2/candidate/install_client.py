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
from copy import deepcopy
import math
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
assert not hasattr(sys,'_item_server_skeleton_r13_probe')
assert navigator.is_ready and not navigator.is_transitioning
assert not navigator.get_entries(), 'World view requires no pre-existing pages'
assert not s.busy and not s.projection_active and not b.preparing_entity
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
player=api.GetLocalPlayerId()
assert player and player!='-1'
foot=b.factory.CreatePos(player).GetFootPos()
assert foot is not None and len(foot)==3 and all(not math.isnan(value) and not math.isinf(value) for value in foot),foot
assert -1024.<foot[1]<4096.,('Player level is not physically loaded',foot)
screen=b.factory.CreateGame(b.level).GetScreenSize()
assert len(screen)==2 and all(value>32 for value in screen),screen
saved={'nonce':'6a73798d9ff44f93b1b9a2ca624820ef','key':'client_anchor_depth_'+'6a73798d9ff44f93b1b9a2ca624820ef','player':player,'foot':foot,
 'navigation':[entry.key for entry in navigator.get_entries()],
 'document':deepcopy(s.editor.document.to_data()),
 'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'camera':deepcopy(dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))),
 'plain':json.loads('{"isEnchanted": false, "newAuxValue": 0, "newItemName": "minecraft:diamond_sword", "userData": {}}'),'actor':None,'create':{'state':'pending','attempted':True},
 'journal':[],'attachments':[],'current':None,'body':None,'control':'world_empty',
 'push_attempted':False,'declared_size':min(240.,screen[0]-32.,screen[1]-32.),
 'size_inputs':screen,'markers':(('native_item_marker_tl', [0, 255, 255]), ('native_item_marker_tr', [255, 0, 255]), ('native_item_marker_bl', [255, 255, 0]), ('native_item_marker_br', [0, 255, 0])),'ui_params':{'scale': 1.4, 'render_depth': -15, 'init_rot_x': 0.0, 'init_rot_y': 0.0, 'init_rot_z': 0.0}}
cam_before=native_camera_snapshot()
assert not cam_before['motions'],('Camera has active motions',cam_before)
for key in ('position','rotation','forward'):
 values=cam_before[key]
 assert values is not None and len(values)==3 and all(not math.isnan(v) and not math.isinf(v) for v in values),(key,values)
forward=cam_before['forward']
length=math.sqrt(sum(v*v for v in forward))
assert length>.000001,('Camera forward is invalid',forward)
position=tuple(cam_before['position'][i]+forward[i]*3./length for i in range(3))
assert -1024.<position[1]<4096.,('Anchor placement is outside loaded height',position)
block=b.factory.CreateBlockInfo(b.level)
empty_cells=[]
for x in range(int(math.floor(position[0]-1.)),int(math.floor(position[0]+1.))+1):
 for y in range(int(math.floor(position[1]-1.)),int(math.floor(position[1]+1.))+1):
  for z in range(int(math.floor(position[2]-1.)),int(math.floor(position[2]+1.))+1):
   cell=(x,y,z)
   value=block.GetBlock(cell)
   assert value is not None and len(value)==2 and value[0]=='minecraft:air',('Placement is not verified loaded air',cell,value)
   empty_cells.append({'position':cell,'block':value})
saved['native_camera']=cam_before
saved['position']=position
saved['empty_cells']=empty_cells
saved['roi_receipt']={'physical_size':[1994,1105],'world':[0,111,1994,1105],'ui':[0,111,1994,1105],
 'declared_before_capture':True,'basis':'fixed native capture extent; top debug band excluded; anchor at camera forward ray distance 3; UI centered declared bounds'}

sys._item_server_skeleton_r13_probe=saved
saved['skeleton_setup']={'model':'modern_projection_diagnostic_item_body_r13','model_id':None,'state':'pending'}
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','foot','position','actor','create','navigation','document','profiles','camera','declared_size','size_inputs','ui_params','native_camera','empty_cells','roi_receipt','skeleton_setup')))
