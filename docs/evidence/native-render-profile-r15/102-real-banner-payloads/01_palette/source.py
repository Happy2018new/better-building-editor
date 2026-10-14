import json,sys,time
import mod.client.extraClientApi as api
from modern_projection.pyreact import navigator
owner=api.GetSystem('ModernProjection','ModernProjectionClientSystem')
assert owner is not None and owner.session is not None, 'Workspace is not initialized'
s=owner.session
b=owner.bridge
low=(0,-57,19)
high=(12,-54,24)
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos(low,high,False)
raw=palette.SerializeBlockPalette()
assert not raw.get('extra'),raw.get('extra')
rows=[]
depth,width,height=raw['volume']
for pos in ((1, -56, 20), (6, -56, 20), (11, -56, 20), (1, -55, 23), (6, -55, 23), (11, -55, 23)):
 local=tuple(pos[i]-low[i] for i in range(3))
 index=local[1]*width*depth+local[0]*depth+local[2]
 found=[(name,actor[index]) for name,actor in raw.get('actor',{}).items() if index in actor]
 assert len(found)==1,(pos,index,raw.get('actor'))
 name,actor=found[0]
 rows.append({'name':name,'pos':pos,'actor':actor})
_result=json.dumps({'engine':api.GetEngineVersion(),'rows':rows,'extra':raw.get('extra')})
