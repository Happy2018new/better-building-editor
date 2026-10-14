import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
cam=b.factory.CreateCamera(b.level)
rows=[]
for name,local in zip(('chest', 'copper_chest', 'ender_chest', 'bed', 'flower_pot'),((1, 1, 1), (4, 1, 1), (7, 1, 1), (10, 1, 1), (13, 1, 1))):
 pos=tuple(s.origin[i]+local[i] for i in range(3))
 points=[cam.WorldToScreenPoint(pos[0]+x,pos[1]+y,pos[2]+z)
  for x in (0.,1.) for y in (0.,1.) for z in (0.,2. if name=='bed' else 1.)]
 rows.append({'name':name,'position':pos,'points':points})
_result=json.dumps(rows)
