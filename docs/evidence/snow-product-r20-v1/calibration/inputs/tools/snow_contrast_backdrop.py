"""Reversible distant contrast wall for the owned snow visual test world."""
SETUP = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
players=api.GetPlayerList()
assert len(players)==1
adapter=WorldAdapter(players[0])
target=%r
lo=(target[0]-2,target[1]-16,target[2]+12)
hi=(target[0]+22,target[1]+24,target[2]+12)
assert -64<=lo[1] and hi[1]<320
palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,lo,hi,False)
assert palette is not None
data=palette.SerializeBlockPalette()
expected_cells=(hi[0]-lo[0]+1)*(hi[1]-lo[1]+1)
assert tuple(data['volume'])==(1,hi[0]-lo[0]+1,hi[1]-lo[1]+1),data['volume']
assert sum(len(indices) for indices in data.get('common',{}).values())==expected_cells,data
assert all(value[0]=='minecraft:air' for layer in ('common','extra') for value in data.get(layer,{})),data
assert not data.get('actor'),data
assert not hasattr(sys,'_snow_contrast_backdrop')
saved={'player':players[0],'dimension':adapter.dimension,'lo':lo,'hi':hi,'journal':[]}
sys._snow_contrast_backdrop=saved
for x in range(lo[0],hi[0]+1):
 for y in range(lo[1],hi[1]+1):
  pos=(x,y,lo[2])
  saved['journal'].append(pos)
  assert adapter.write(pos,('minecraft:black_concrete',0)),pos
_result=json.dumps({'lo':lo,'hi':hi,'cells':len(saved['journal']),
 'minimum_neighbor_distance':12,'material':'minecraft:black_concrete'})
'''

RESTORE = '''import json,sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
saved=getattr(sys,'_snow_contrast_backdrop',None)
if saved is None:
 _result=json.dumps({'restored':True,'cells':0,'journal_absent':True})
else:
 adapter=WorldAdapter(saved['player'])
 assert adapter.dimension==saved['dimension']
 for pos in reversed(saved['journal']):assert adapter.write(tuple(pos),('minecraft:air',0)),pos
 palette=adapter.palette_block.GetBlockPaletteBetweenPos(adapter.dimension,tuple(saved['lo']),tuple(saved['hi']),False)
 assert palette is not None
 data=palette.SerializeBlockPalette()
 assert all(value[0]=='minecraft:air' for layer in ('common','extra') for value in data.get(layer,{})),data
 assert not data.get('actor'),data
 del sys._snow_contrast_backdrop
 _result=json.dumps({'restored':True,'cells':len(saved['journal'])})
'''
