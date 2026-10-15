"""A journaled direct-setter control for the snow suite's distant native wall."""

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
  assert adapter.info.SetBlockNew(pos,{'name':'minecraft:black_concrete','aux':0},0,adapter.dimension,True,True),pos
  actual=adapter.info.GetBlockNew(pos,adapter.dimension)
  assert actual and actual['name']=='minecraft:black_concrete' and actual['aux']==0,(pos,actual)
_result=json.dumps({'lo':lo,'hi':hi,'cells':len(saved['journal']),
 'minimum_neighbor_distance':12,'material':'minecraft:black_concrete',
 'write_path':'SetBlockNew legacy=True updateNeighbors=True',
 'server_material_readback':True})
'''
