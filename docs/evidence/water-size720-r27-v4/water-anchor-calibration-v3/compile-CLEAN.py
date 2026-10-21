import json,sys
import mod.client.extraClientApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
from modern_projection.pyreact import navigator
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
