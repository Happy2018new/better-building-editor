# -*- coding: utf-8 -*-
"""Read-only ordinary Scene telemetry and paired restoration payloads."""

PREFIX = '''import json,sys
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
from modern_projection.projection.widgets import Theme
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
s=owner.session;b=owner.bridge
'''

SAVE = '''assert not hasattr(sys,'_r27_water_gui_scene')
assert navigator.top is None and not navigator.is_transitioning
assert not s.busy and s.edit_job is None and s.io_job is None and not s.projection_active
assert callable(getattr(s.liquid_profile,'ui_offset_for_gui',None))
sys._r27_water_gui_scene={'grid':s.grid,'theme':(Theme.scale,Theme.motion),
 'profile':s.liquid_profile,'factory':b.factory}
s.grid=False
_result=True
'''

NATIVE_GUI = '''game=b.factory.CreateGame(b.level)
logical=tuple(game.GetScreenSize());physical=tuple(game.GetScreenViewInfo())
_result=json.dumps({'logical':logical,'screen_view_info':physical,
 'sdk_integer_gui':max(1.,round(float(physical[0])/logical[0])),
 'cached_gui':Theme.native_gui_scale,'theme_scale':Theme.scale,'font':Theme.input_font_scale})
'''

SAME_FONT = '''Theme.configure(3.,True)
''' + NATIVE_GUI

RESTORE_THEME = '''saved=sys._r27_water_gui_scene
Theme.configure(*saved['theme'])
_result=True
'''

EXTRA_STATE = '''from modern_projection.projection.widgets import Theme
row=json.loads(_result)
game=b.factory.CreateGame(b.level)
logical=tuple(game.GetScreenSize());physical=tuple(game.GetScreenViewInfo())
row['gui_cache']={'logical':logical,'screen_view_info':physical,
 'sdk_integer_gui':max(1.,round(float(physical[0])/logical[0])),
 'cached_gui':Theme.native_gui_scale,'theme_scale':Theme.scale,'font':Theme.input_font_scale}
row['native_water_controls']=[]
controls=s.liquid_controls
if controls is not None:
 for key,entry in sorted(controls.registry.items(),key=lambda item:repr(item[0])):
  renderer=entry.get('renderer')
  banks=[]
  for slot,ref in enumerate(entry['dolls']):
   control=ref.current
   surface=entry['surfaces'][slot].current
   banks.append(None if control is None else {'slot':slot,'position':control.GetPosition(),
    'global_position':control.GetGlobalPosition(),'size':control.GetSize(),
    'native_visible':control.GetVisible(),'surface_visible':surface.GetVisible() if surface is not None else None,
    'native_model_id':control.asNeteasePaperDoll().GetModelId(),
    'declared_visible':renderer.visible[slot] if renderer is not None else None,
    'renderer_model_id':renderer.ids[slot] if renderer is not None else None})
  row['native_water_controls'].append({'key':repr(key),'geometry':entry.get('geometry'),
   'front':renderer.front if renderer is not None else None,'banks':banks,
   'renderer_error':renderer.error if renderer is not None else None,
   'request_ready':entry.get('ready_request') is not None})
_result=json.dumps(row)
'''

CLOSE = '''assert not navigator.is_transitioning
if navigator.top is not None:
 assert navigator.top.key=='modern_projection_workspace'
 assert navigator.pop()
_result=True
'''

CLOSED = '''_result=json.dumps({'closed':navigator.top is None and not navigator.is_transitioning})
'''

RESTORE_OWN = '''saved=getattr(sys,'_r27_water_gui_scene',None)
if saved is not None:
 s.grid=saved['grid']
 assert s.liquid_profile is saved['profile']
 assert b.factory is saved['factory']
 Theme.configure(*saved['theme'])
 s.emit()
 del sys._r27_water_gui_scene
_result=True
'''

RESTORED = '''_result=json.dumps({'restored':not hasattr(sys,'_r27_water_gui_scene')
 and not hasattr(sys,'_blueprint_qa_saved') and navigator.top is None and not navigator.is_transitioning,
 'own_marker':hasattr(sys,'_r27_water_gui_scene'),'blueprint_marker':hasattr(sys,'_blueprint_qa_saved'),
 'navigator_top':None if navigator.top is None else navigator.top.key,
 'navigator_transitioning':navigator.is_transitioning,
 'busy':s.busy,'edit_job':s.edit_job is not None,'io_job':s.io_job is not None,
 'projection_active':s.projection_active,'world_actors':len(b.projection_entities)+int(bool(b.entity)),
 'preparing_entity':bool(b.preparing_entity)})
'''
