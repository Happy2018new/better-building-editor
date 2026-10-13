def _scaffold_single_air_control(config):
 import math,traceback
 import mod.server.extraServerApi as api
 result={'schema':1,'kind':'scaffold_single_air_api_control','method':'single nearby natural air to stone to explicit dual-layer air; native raw states; synchronous restore; v1','config':config,
         'runtime':api.GetMinecraftVersion(),'admitted':False,'completed':False,
         'restored':False,'mutation_attempted':False,'ground':None,'initial':None,
         'stone':None,'explicit_air':None,'cleanup':None,'error':None,'cleanup_error':None,
         'capability':'unknown_not_classified_by_api_diagnostic',
         'acceptance':{'editor':'pending','full':'pending','missing':'pending'}}
 assert result['runtime']==config['runtime'],'Runtime differs'
 players=api.GetPlayerList()
 assert len(players)==1 and players[0]==config['player'],'Owned player differs'
 factory=api.GetEngineCompFactory()
 foot=factory.CreatePos(players[0]).GetFootPos()
 dimension=factory.CreateDimension(players[0]).GetEntityDimensionId()
 result.update({'player':players[0],'foot':foot,'dimension':dimension})
 assert foot is not None and -64<=foot[1]<=320 and all(-1000000<=v<=1000000 for v in foot),'Invalid foot'
 assert all(abs(foot[i]-config['foot'][i])<=.125 for i in range(3)),'Anchor moved'
 assert dimension==config['dimension']==0,'Dimension differs'
 base=tuple(int(math.floor(v)) for v in foot)
 pos=tuple(config['pos'])
 assert pos==(base[0]+4,base[1]+2,base[2]+4),'Single nearby coordinate differs'
 info=factory.CreateBlockInfo(api.GetLevelId())
 state=factory.CreateBlockState(api.GetLevelId())
 block=factory.CreateBlock(api.GetLevelId())
 def read(at):
  return {'pos':at,'front':info.GetBlockNew(at,dimension),
          'states':state.GetBlockStates(at,dimension),'liquid':info.GetLiquidBlock(at,dimension)}
 def dry_air(value):
  front,liquid=value['front'],value['liquid']
  return (isinstance(front,dict) and front=={'name':'minecraft:air','aux':0}
   and type(front.get('aux')) is int and (liquid is None or isinstance(liquid,dict)
   and liquid.get('name')=='minecraft:air' and type(liquid.get('aux',0)) is int and liquid.get('aux',0)==0))
 result['ground']=read((base[0],base[1]-1,base[2]))
 ground=result['ground']
 assert isinstance(ground['front'],dict) and ground['front'].get('name') not in (None,'minecraft:air','minecraft:unknown') and isinstance(ground['states'],dict),'Loaded ground unavailable'
 result['initial']=read(pos)
 assert dry_air(result['initial']),'Reserve is not dry air'
 assert result['initial']['states'] is None or result['initial']['states']=={},'Unexpected native air states'
 air=block.GetBlankBlockPalette()
 assert air is not None,'Missing dual-layer air palette'
 result['air_deserialize_returned']=air.DeserializeBlockPalette({
  'volume':(1,1,1),'common':{('minecraft:air',0):[0]},'states':{},
  'extra':{('minecraft:air',0):[0]},'extraStates':{},'actor':{},'void':False,'eliminateAir':False})
 assert result['air_deserialize_returned'] is True,'Air palette rejected'
 result['admitted']=True
 try:
  result['mutation_attempted']=True
  returned=info.SetBlockNew(pos,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
  result['stone']={'returned':returned,'readback':read(pos)}
  positive=result['stone']['readback']
  result['stone_positive']=(returned is True and positive['front']=={'name':'minecraft:stone','aux':0}
   and type(positive['front'].get('aux')) is int and positive['states']=={} and positive['liquid'] is None)
  assert result['stone_positive'],'Native stone positive control failed'
  returned=block.SetBlockByBlockPalette(air,dimension,pos,0,0)
  result['explicit_air']={'returned':returned,'readback':read(pos)}
  assert returned is True and dry_air(result['explicit_air']['readback']),'Explicit air write failed'
  result['completed']=True
 except Exception as error:
  result['error']='%s: %s'%(type(error).__name__,error)
  traceback.print_exc()
 finally:
  try:
   returned=block.SetBlockByBlockPalette(air,dimension,pos,0,0)
   actual=read(pos)
   result['cleanup']={'returned':returned,'readback':actual,
                      'raw_states_equal_initial':actual['states']==result['initial']['states']}
   result['restored']=returned is True and dry_air(actual)
  except Exception as error:
   result['cleanup_error']='%s: %s'%(type(error).__name__,error)
   traceback.print_exc()
 if not result['restored']:result['completed']=False
 return result
_result=_scaffold_single_air_control({'runtime': '1.21.120.0', 'player': '-8589934591', 'foot': (0.5, -60.0, 0.5), 'dimension': 0, 'pos': (4, -58, 4)})
del _scaffold_single_air_control
