def _scaffold_air_readback():
 import math
 import mod.server.extraServerApi as api
 result={'schema':1,'kind':'scaffold_raw_air_readback','method':'readonly native ground and17reserve offsets at foot+2 and foot+18; raw states preserved; v1','runtime':api.GetMinecraftVersion(),
         'player':None,'foot':None,'dimension':None,'ground':None,'planes':[],'mutations':[]}
 players=api.GetPlayerList()
 if not players:return result
 player=players[0]
 factory=api.GetEngineCompFactory()
 foot=factory.CreatePos(player).GetFootPos()
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 result.update({'player':player,'foot':foot,'dimension':dimension})
 if foot is None or not -64<=foot[1]<=320:return result
 base=tuple(int(math.floor(value)) for value in foot)
 info=factory.CreateBlockInfo(api.GetLevelId())
 state=factory.CreateBlockState(api.GetLevelId())
 def read(pos):
  return {'pos':pos,'front':info.GetBlockNew(pos,dimension),
          'states':state.GetBlockStates(pos,dimension),'liquid':info.GetLiquidBlock(pos,dimension)}
 result['ground']=read((base[0],base[1]-1,base[2]))
 for height in (2, 18):
  origin=(base[0]+4,base[1]+height,base[2]+4)
  plane={'height_above_foot':height,'origin':origin,'cells':[]}
  for offset in ((0, -1, 0), (-1, -1, 0), (1, -1, 0), (0, -1, -1), (0, -1, 1), (0, 0, 0), (-1, 0, 0), (1, 0, 0), (0, 0, -1), (0, 0, 1), (0, 1, 0), (-1, 1, 0), (1, 1, 0), (0, 1, -1), (0, 1, 1), (0, 2, 0), (0, 3, 0)):
   pos=tuple(origin[index]+offset[index] for index in range(3))
   plane['cells'].append(dict(read(pos),offset=offset))
  result['planes'].append(plane)
 return result
_result=_scaffold_air_readback()
del _scaffold_air_readback
