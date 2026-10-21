import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
from modern_projection.pyreact import Component,Panel,Image,Style,Color,Position,PaperDollRenderType,use_ref,use_state,navigator
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
 viewport=use_ref(None)
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
  current['refs'],current['stone'],current['viewport']=refs,stone,viewport
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
 children=[Doll(ref=stone,managed=True,renderType=PaperDollRenderType.block_geometry,
   style=Style(position=Position.absolute,left=0,top=0,width=rw,height=rh,zIndex=50))]
 for slot,ref in enumerate(refs):
  children.append(Doll(key=str(slot),ref=ref,managed=True,renderType=PaperDollRenderType.skeleton,
   style=Style(position=Position.absolute,left=0,top=offset,width=rw,height=rh,zIndex=60)))
 return Panel(style=Style(width=width,height=height),children=[
  Image(color=Color(0xF0F0F0FF),style=Style(position=Position.absolute,left=0,top=0,width=width,height=height,zIndex=0)),
  Panel(ref=viewport,style=Style(position=Position.absolute,left=left,top=top,width=rw,height=rh,zIndex=50),children=children)])
assert navigator.push(R27WaterAnchorUI(),key='r27_water_anchor_diagnostic')
_result=json.dumps({'opened':True,'logical':logical,'screen_view_info':physical,'gui':gui,
 'style':'raw Style, without widgets.S/Theme.scale'})
