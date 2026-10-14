import json,sys
import mod.server.extraServerApi as api
factory=api.GetEngineCompFactory()
level=api.GetLevelId()
player=api.GetPlayerList()[0]
info=factory.CreateBlockInfo(player)
state=factory.CreateBlockState(level)
dimension=factory.CreateDimension(player).GetEntityDimensionId()
assert dimension==0
saved=api._native_banner_items
for entry in reversed(saved['journal']):
 info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,True)
 if entry['nbt']:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
del api._native_banner_items
_result=True
