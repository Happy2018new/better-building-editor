# pylint: disable=unexpected-keyword-arg,E1123
from modern_projection.pyreact import Component,Image,Color,PaperDoll,Style,use_ref,AlignItems,JustifyContent,PaperDollRenderType,Position
from modern_projection.projection.bridge import _stable_palette
from modern_projection.projection import static_frame_item_data
from copy import deepcopy
assert not hasattr(sys,'_native_item_ui_probe')
assert not navigator.is_transitioning and navigator.is_ready
assert not s.busy and not s.projection_active and not b.preparing_entity
assert not any(profile['accepted'] for profile in static_frame_item_data.FRAME_ITEMS.values())
player=api.GetLocalPlayerId()
assert player and player!='-1'
native_screen=b.factory.CreateGame(b.level).GetScreenSize()
assert len(native_screen)==2 and all(value>32 for value in native_screen),native_screen
probe_size=min(240.,native_screen[0]-32.,native_screen[1]-32.)
assert probe_size>0,probe_size
markers=[{'key':'native_item_marker_tl','rgb':[0,255,255],'x':8.,'y':8.,'size':6.},
 {'key':'native_item_marker_tr','rgb':[255,0,255],'x':native_screen[0]-14.,'y':8.,'size':6.},
 {'key':'native_item_marker_bl','rgb':[255,255,0],'x':8.,'y':native_screen[1]-14.,'size':6.},
 {'key':'native_item_marker_br','rgb':[0,255,0],'x':native_screen[0]-14.,'y':native_screen[1]-14.,'size':6.}]
bone=b.factory.CreateActorRender(player).GetQueryableBoneOrientation('head',False)
assert bone is not None and len(bone)==4,bone
saved={'nonce':'7ee4f8762d504c39a330693190cb19e9','key':'native_item_ui_'+'7ee4f8762d504c39a330693190cb19e9','player':player,'bone':bone,
 'navigation':[entry.key for entry in navigator.get_entries()],
 'document':deepcopy(s.editor.document.to_data()),'profiles':repr(_stable_palette(static_frame_item_data.FRAME_ITEMS)),
 'camera':deepcopy(dict((key,getattr(s,key)) for key in ('camera_pose','camera_pivot','camera_pan','camera_depth_pose'))),
 'items':json.loads('{"actual_enchanted": {"isEnchanted": true, "newAuxValue": 0, "newItemName": "minecraft:diamond_sword", "userData": {"ench": [{"id": {"__type__": 2, "__value__": 9}, "lvl": {"__type__": 2, "__value__": 3}, "modEnchant": {"__type__": 8, "__value__": ""}}]}}, "flag_enchanted": {"isEnchanted": true, "newAuxValue": 0, "newItemName": "minecraft:diamond_sword", "userData": {}}, "plain": {"isEnchanted": false, "newAuxValue": 0, "newItemName": "minecraft:diamond_sword", "userData": {}}}'),'attachments':[],'current':None,'control':'empty','push_attempted':False,
 'declared_size':probe_size,'size_inputs':native_screen,'markers':markers,
 'ui_params':{'entity_id':player,'scale':1.,'render_depth':-50,'init_rot_x':0.,'init_rot_y':60.,'init_rot_z':0.}}
sys._native_item_ui_probe=saved
@Component
def NativeItemPaperDollProbe():
 root_ref=use_ref(None)
 ref=use_ref(None)
 marker_refs=[use_ref(None),use_ref(None),use_ref(None),use_ref(None)]
 saved['root_ref']=root_ref
 saved['ref']=ref
 saved['marker_refs']=marker_refs
 children=[PaperDoll(key='native_item_probe_doll',ref=ref,renderType=PaperDollRenderType.entity,
  entityId=player,scale=1.,renderDepth=-50,initRotX=0.,initRotY=60.,initRotZ=0.,
  style=Style(width=probe_size,height=probe_size))]
 for index,marker in enumerate(markers):
  rgb=marker['rgb']
  children.append(Image(key=marker['key'],ref=marker_refs[index],
   color=Color((rgb[0]<<24)|(rgb[1]<<16)|(rgb[2]<<8)|255),
   style=Style(position=Position.absolute,left=marker['x'],top=marker['y'],width=6.,height=6.)))
 return Image(key='native_item_probe_root',ref=root_ref,color=Color(0xF7F9FCFF),style=Style(width='100%',height='100%',alignItems=AlignItems.center,
  justifyContent=JustifyContent.center),children=children)
saved['push_attempted']=True
assert navigator.push(NativeItemPaperDollProbe(),key=saved['key'])
_result=json.dumps(dict((key,saved[key]) for key in ('nonce','key','player','bone','navigation','document','profiles','camera','ui_params','declared_size','size_inputs','markers')))
