# -*- coding: utf-8 -*-
# pylint: disable=unexpected-keyword-arg,E1123
"""Python 2 payloads for one isolated neutral-cube/matrix diagnostic UI."""

PREFIX = '''import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
'''

OPEN = '''from modern_projection.pyreact import Component,Panel,Image,Style,Color,Position,PaperDollRenderType,use_ref,use_state,navigator
from modern_projection.pyreact.hooks import use_animation_frame
from modern_projection.projection.widgets import Doll
from modern_projection.projection.liquid_render import SkeletonLiquidRenderer
assert not navigator.is_transitioning
assert navigator.top is None or navigator.top.key=='modern_projection_workspace'
assert not hasattr(sys,'_r27_water_anchor_ui')
game=factory.CreateGame(level)
logical=tuple(game.GetScreenSize())
physical=tuple(game.GetScreenViewInfo())
gui=max(1.,round(float(physical[0])/logical[0]))
assert abs(physical[0]/gui-logical[0])<=1.1
assert abs(physical[1]/gui-logical[1])<=1.1
sys._r27_water_anchor_ui={'renderer':None,'refs':None,'frames':0,'stable_frames':0,
 'closing':False,'config':None,'set_config':None,'rendered_config':None,'ready':False,
 'group':None,'pose':(.1,-90.,0.,0.),'stone_request':None,'stone_visible':False,
 'logical':logical,'physical':physical,'gui':gui,'all_ids':[]}
@Component
def R27WaterAnchorUI():
 config,set_config=use_state(None)
 refs=[use_ref(None),use_ref(None)]
 stone=use_ref(None)
 saved=sys._r27_water_anchor_ui
 saved['set_config']=set_config
 saved['rendered_config']=config
 width,height=saved['logical']
 rect=(0.,0.,float(width),float(height)) if config is None else tuple(config['rect'])
 left,top,rw,rh=rect
 factor=0. if config is None else config['offset_factor']
 offset=min(rw,rh)*factor
 def tick(now):
  current=getattr(sys,'_r27_water_anchor_ui',None)
  if current is None or current['closing']:return
  current['refs'],current['stone']=refs,stone
  if not all(ref.current for ref in refs+[stone]):return
  if current['renderer'] is None:
   def show(slot,visible):refs[slot].current.SetVisible(visible)
   current['renderer']=SkeletonLiquidRenderer([ref.current.asNeteasePaperDoll() for ref in refs],factory.CreateModel(None),show)
  ready=current['renderer'].update(current['group'],current['pose'],now)
  stone.current.SetVisible(current['stone_visible'])
  if current['stone_visible'] and current['stone_request']!=current.get('desired_stone_request'):
   name,pose=current['desired_stone_request']
   scale,x,y,z=pose
   assert stone.current.asNeteasePaperDoll().RenderBlockGeometryModel({
    'block_geometry_model_name':name,'scale':scale,'init_rot_x':x,'init_rot_y':y,'init_rot_z':z})
   current['stone_request']=current['desired_stone_request']
  current['ready']=ready and current['rendered_config']==current['config']
  current['stable_frames']=current['stable_frames']+1 if current['ready'] else 0
  current['frames']+=1
 use_animation_frame(tick)
 children=[Image(color=Color(0xF0F0F0FF),style=Style(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Doll(ref=stone,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=Style(position=Position.absolute,left=left,top=top,width=rw,height=rh,zIndex=50))]
 for slot,ref in enumerate(refs):
  children.append(Doll(key=str(slot),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=Style(position=Position.absolute,left=left,top=top+offset,width=rw,height=rh,zIndex=60)))
 return Panel(style=Style(width=width,height=height),children=children)
assert navigator.push(R27WaterAnchorUI(),key='r27_water_anchor_diagnostic')
_result=json.dumps({'opened':True,'logical':logical,'screen_view_info':physical,'gui':gui,
 'style':'raw Style, without widgets.S/Theme.scale'})
'''

CONFIGURE = '''from collections import namedtuple
from modern_projection.projection.model import Document
from modern_projection.projection.liquid_transport import RenderGroup,pack_group
config=%r
saved=sys._r27_water_anchor_ui
bridge=api.GetSystem('ModernProjection','ModernProjectionClientSystem').bridge
position=tuple(config['position'])
pose=tuple(config['pose'])
rect=tuple(config['rect'])
unit=min(rect[2:])*config['unit_fraction']
mode=config['mode']
if mode=='stone':
 name=bridge.geometry(Document(size=(4,4,4),blocks={position:('minecraft:stone',0)}))
 assert name
 saved['desired_stone_request']=(name,(unit/10.,pose[0]-90.,pose[1],pose[2]))
saved['stone_visible']=mode=='stone'
saved['pose']=(unit/min(rect[2:]),pose[0]-90.,pose[1],pose[2])
Surface=namedtuple('R27AnchorSurface','position layer heights faces texture_key flow_uv')
payload=pack_group((0,0,0),(Surface(position,0,(1.,)*4,63,'still_water_grey',None),),(0,0,0),1.,1.)
if mode=='matrix':payload=payload[:3]+((39686.,-1.,float(config['matrix_selected']),1.),)
group=None if mode in ('empty','stone') else RenderGroup((mode,position,config['model']),config['model'],(0,0,0),payload)
saved['group']=group
saved['config']=config
saved['ready']=False
saved['stable_frames']=0
saved['set_config'](config)
_result=json.dumps({'configured':config,'unit':unit,'skeleton_pose':saved['pose'],
 'stone_request':saved.get('desired_stone_request'),'payload':payload})
'''

STATUS = '''from modern_projection.pyreact import navigator
saved=sys._r27_water_anchor_ui
renderer=saved['renderer']
refs=saved['refs'] or []
native=[]
for ref in refs+[saved.get('stone')]:
 if ref is not None and ref.current is not None:
  control=ref.current
  native.append({'position':control.GetPosition(),'global_position':control.GetGlobalPosition(),
   'size':control.GetSize(),'model_id':control.asNeteasePaperDoll().GetModelId()})
state=None if renderer is None else {'front':renderer.front,'ids':renderer.ids,'visible':renderer.visible,
 'pending':renderer.pending is not None,'error':renderer.error,'closed':renderer.closed,
 'native_ids':[doll.GetModelId() for doll in renderer.dolls]}
ready=bool(renderer is not None and saved['ready'] and saved['stable_frames']>=3
 and navigator.top and navigator.top.key=='r27_water_anchor_diagnostic' and not navigator.is_transitioning)
_result=json.dumps({'ready':ready,'stable_frames':saved['stable_frames'],'frames':saved['frames'],
 'config':saved['config'],'native':native,'renderer':state,'logical':factory.CreateGame(level).GetScreenSize(),
 'screen_view_info':factory.CreateGame(level).GetScreenViewInfo()})
'''

CLEAN = '''from modern_projection.pyreact import navigator
saved=getattr(sys,'_r27_water_anchor_ui',None)
if saved is not None:
 saved['closing']=True
 renderer=saved['renderer']
 if renderer is not None:
  renderer.close()
  assert renderer.closed and not any(renderer.visible)
 if navigator.top and navigator.top.key=='r27_water_anchor_diagnostic':assert navigator.pop()
 del sys._r27_water_anchor_ui
_result=True
'''

CLEAN_READY = '''from modern_projection.pyreact import navigator
_result=json.dumps({'restored':not hasattr(sys,'_r27_water_anchor_ui') and not navigator.is_transitioning
 and (navigator.top is None or navigator.top.key=='modern_projection_workspace')})
'''
