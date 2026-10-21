import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
from collections import namedtuple
from modern_projection.projection.model import Document
from modern_projection.projection.liquid_transport import RenderGroup,pack_group
config={'position': [1, 1, 1], 'pose': [0.0, 0.0, 0.0], 'rect': [10.0, 20.0, 200.0, 100.0], 'unit_fraction': 0.18, 'mode': 'empty', 'model': 'modern_projection_r27_anchor_15', 'offset_factor': 0.0}
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
