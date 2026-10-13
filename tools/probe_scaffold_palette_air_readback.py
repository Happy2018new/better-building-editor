"""Read native one-cell palette encoding at dry air and loaded ground.

No block, actor, item, inventory, rule, UI or window mutation is performed.
Native palette bytes are represented by their original repr and typed buckets.
"""
SERVER = '''def _scaffold_palette_air_readback_r14():
 import math
 import mod.server.extraServerApi as api
 assert api.GetMinecraftVersion()=='1.21.120.0','Runtime differs'
 players=api.GetPlayerList()
 assert len(players)==1,'Expected one owned player'
 factory=api.GetEngineCompFactory()
 player=players[0]
 foot=factory.CreatePos(player).GetFootPos()
 dimension=factory.CreateDimension(player).GetEntityDimensionId()
 assert dimension==0 and foot is not None and -64<=foot[1]<=320,'World not initialized'
 base=tuple(int(math.floor(axis)) for axis in foot)
 ground=(base[0],base[1]-1,base[2])
 nearby=(base[0]+4,base[1]+2,base[2]+4)
 info=factory.CreateBlockInfo(api.GetLevelId())
 state=factory.CreateBlockState(api.GetLevelId())
 block=factory.CreateBlock(api.GetLevelId())
 def read(at):
  return {'pos':at,'front':info.GetBlockNew(at,dimension),
   'states':state.GetBlockStates(at,dimension),'liquid':info.GetLiquidBlock(at,dimension)}
 ground_read=read(ground)
 assert ground_read['front']['name'] in ('minecraft:grass_block','minecraft:grass','minecraft:stone','minecraft:dirt') and isinstance(ground_read['states'],dict),'Loaded nonactor ground unavailable'
 air_read=read(nearby)
 assert air_read['front']=={'name':'minecraft:air','aux':0} and type(air_read['front']['aux']) is int,'Nearby reserve occupied'
 assert air_read['states'] is None or air_read['states']=={},'Unexpected native air states'
 assert air_read['liquid'] is None,'Nearby reserve contains liquid'
 result={'schema':1,'kind':'scaffold_palette_air_readback','runtime':api.GetMinecraftVersion(),
  'player':player,'foot':foot,'dimension':dimension,'mutations':[],
  'acceptance':{'editor':'pending','full':'pending','missing':'pending'},'cells':[]}
 for label,actual in (('loaded_ground',ground_read),('natural_air',air_read)):
  palette=block.GetBlockPaletteBetweenPos(dimension,actual['pos'],actual['pos'],False)
  assert palette is not None,'Native palette unavailable'
  data=palette.SerializeBlockPalette()
  assert isinstance(data,dict),'Native palette serialization missing'
  row={'label':label,'readback':actual,'raw_palette_repr':repr(data),'keys':sorted(data),
   'volume':data.get('volume'),'void':data.get('void'),'eliminateAir':data.get('eliminateAir'),
   'common':None,'extra':None,'states_repr':repr(data.get('states')),
   'extraStates_repr':repr(data.get('extraStates')),'actor_repr':repr(data.get('actor'))}
  for key in ('common','extra'):
   if isinstance(data.get(key),dict):
    row[key]=[[list(material),list(indices)] for material,indices in sorted(data[key].items())]
  result['cells'].append(row)
 return result
_result=_scaffold_palette_air_readback_r14()
del _scaffold_palette_air_readback_r14
'''
