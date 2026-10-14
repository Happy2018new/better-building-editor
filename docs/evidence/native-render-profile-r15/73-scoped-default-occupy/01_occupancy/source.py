import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
player=api.GetPlayerList()[0]
dimension=factory.CreateDimension(player).GetEntityDimensionId()
info=factory.CreateBlockInfo(player)
assert dimension==0
positions=((1, -56, 1), (4, -56, 1), (7, -56, 1), (10, -56, 1), (13, -56, 1))
restore=False
if not hasattr(sys,'_native_r15_occupied'):sys._native_r15_occupied={}
saved=sys._native_r15_occupied
rows=[]
for pos in positions:
 if restore:
  before=saved.pop(pos)
  info.SetBlockNew(pos,before,0,dimension,True,False)
 else:
  assert pos not in saved
  before=info.GetBlockNew(pos,dimension)
  assert before['name']=='minecraft:air',before
  saved[pos]=before
  info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
 rows.append({'pos':pos,'before':before,'after':info.GetBlockNew(pos,dimension)})
_result=json.dumps(rows)
