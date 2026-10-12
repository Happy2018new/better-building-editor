from copy import deepcopy
import math
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
assert not hasattr(sys,'_client_anchor_ui_probe')
assert navigator.is_ready and not navigator.is_transitioning
assert not s.busy and not s.projection_active and not b.preparing_entity
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
player=api.GetLocalPlayerId()
assert player and player!='-1'
foot=b.factory.CreatePos(player).GetFootPos()
assert foot is not None and len(foot)==3 and all(not math.isnan(value) and not math.isinf(value) for value in foot),foot
assert -1024.<foot[1]<4096.,('Player level is not physically loaded',foot)
screen=b.factory.CreateGame(b.level).GetScreenSize()
assert len(screen)==2 and all(value>32 for value in screen),screen
saved={'nonce':'91e00c4b19ed4ef68850a59a69f64f3d','key':'client_anchor_ui_'+'91e00c4b19ed4ef68850a59a69f64f3d','player':player,'foot':foot,
 'navigation':[entry.key for entry in navigator.get_entries()],
 'document':deepcopy(s.editor.document.to_data()),
 'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'camera':deepcopy(dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))),
 'plain':json.loads('{"isEnchanted": false, "newAuxValue": 0, "newItemName": "minecraft:diamond_sword", "userData": {}}'),'actor':None,'create':{'state':'pending','attempted':True},
 'journal':[],'attachments':[],'current':None,'body':None,'control':'empty',
 'push_attempted':False,'declared_size':min(240.,screen[0]-32.,screen[1]-32.),
 'size_inputs':screen,'markers':(('native_item_marker_tl', [0, 255, 255]), ('native_item_marker_tr', [255, 0, 255]), ('native_item_marker_bl', [255, 255, 0]), ('native_item_marker_br', [0, 255, 0])),'ui_params':{'scale': 0.35, 'render_depth': -50, 'init_rot_x': 0.0, 'init_rot_y': 0.0, 'init_rot_z': 0.0}}
sys._client_anchor_ui_probe=saved
saved['position']=(foot[0],foot[1]+1.,foot[2])
candidate=b.system.CreateClientEntityByTypeStr('modern_projection:anchor',saved['position'],(0.,0.))
saved['create']['value']=candidate
saved['create']['state']='returned'
if candidate is not None and candidate!='':
 saved['create']['state']='invalid_return'
 assert isinstance(candidate,basestring) and candidate not in ('-1',player),saved['create']
 saved['actor']=candidate
 saved['create']['state']='returned'
assert saved['actor'] is not None,saved['create']
saved['ui_params']['entity_id']=saved['actor']
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','foot','position','actor','create','navigation','document','profiles','camera','declared_size','size_inputs','ui_params')))
