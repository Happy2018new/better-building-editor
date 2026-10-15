"""Record native player placement and actor fixtures in the owned disposable world."""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value

SERVER = '''import json, math, sys
import mod.server.extraServerApi as api
from modern_projection.server_system import WorldAdapter
f=api.GetEngineCompFactory()
p=api.GetPlayerList()[0]
d=f.CreateDimension(p).GetEntityDimensionId()
b=f.CreateBlockInfo(p)
st=f.CreateBlockState(api.GetLevelId())
it=f.CreateItem(p)
a=WorldAdapter(p)
'''
CLIENT = '''import json,sys
import mod.client.extraClientApi as api
f=api.GetEngineCompFactory()
b=f.CreateBlock(api.GetLevelId())
bi=f.CreateBlockInfo(api.GetLevelId())
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result = {'schema': 1, 'placements': [], 'actors': []}
    with Client(timeout=30) as client:
        def execute(code, side=False):
            value = return_value(client.call('execute_code', {
                'code': (CLIENT if side else SERVER) + code,
                'is_client': side, 'direct_return': True}))
            return json.loads(value) if isinstance(value, str) else value

        fixture = execute('''foot=f.CreatePos(p).GetFootPos()
origin=(int(math.floor(foot[0]))+5,int(math.floor(foot[1]))+10,int(math.floor(foot[2]))+5)
positions=[(origin[0]+i*3,origin[1],origin[2]) for i in range(10)]
for pos in positions:
 for dx in (0,1):
  for dy in (-1,0,1):
   q=(pos[0]+dx,pos[1]+dy,pos[2])
   previous=b.GetBlockNew(q,d)
   assert previous and previous['name']=='minecraft:air',repr((q,previous))
for pos in positions:
 for dx in (0,1):
  a.write((pos[0]+dx,pos[1]-1,pos[2]),('minecraft:stone',0))
sys._p0_acceptance_positions=positions
_result=json.dumps({'positions':positions,'dimension':d,'foot':foot})''')
        result.update(fixture=fixture)
        positions = [tuple(pos) for pos in fixture['positions']]
        for index, name in enumerate(('oak_fence', 'stone', 'oak_stairs', 'oak_slab',
                                      'short_grass', 'glass_pane')):
            pos = positions[index]
            row = execute('''pos=%r
a.write(pos,('minecraft:water',0))
it.SpawnItemToPlayerCarried({'itemName':%r,'count':1,'auxValue':0},p)
_result=True''' % (pos, 'minecraft:' + name))
            time.sleep(.15)
            used = execute('''pos=%r
used=b.PlayerUseItemToPos((pos[0],pos[1]-1,pos[2]),api.GetMinecraftEnum().ItemPosType.CARRIED,0,1)
_result=json.dumps({'used':used})''' % (pos,))
            time.sleep(.15)
            read = execute('''pos=%r
_result=json.dumps({'front':b.GetBlockNew(pos,d),'states':st.GetBlockStates(pos,d),
 'liquid':b.GetLiquidBlock(pos,d)})''' % (pos,))
            result['placements'].append(dict(read, name=name, pos=pos, use=used))

        for index, name in enumerate(('wooden_door', 'bed', 'chest', 'copper_chest'), 6):
            pos = positions[index]
            execute('''it.SpawnItemToPlayerCarried({'itemName':%r,'count':1,'auxValue':0},p)
_result=True''' % ('minecraft:' + name,))
            time.sleep(.15)
            used = execute('''pos=%r
_result=b.PlayerUseItemToPos((pos[0],pos[1]-1,pos[2]),api.GetMinecraftEnum().ItemPosType.CARRIED,0,1)''' % (pos,))
            time.sleep(.15)
            if name.endswith('chest'):
                execute('''pos=%r
_result=b.PlayerUseItemToPos((pos[0]+1,pos[1]-1,pos[2]),api.GetMinecraftEnum().ItemPosType.CARRIED,0,1)''' % (pos,))
                time.sleep(.15)
            read = execute('''pos=%r
cells=[]
for dx in (-1,0,1):
 for dy in (0,1):
  for dz in (-1,0,1):
   q=(pos[0]+dx,pos[1]+dy,pos[2]+dz)
   front=b.GetBlockNew(q,d)
   if front and front['name']!='minecraft:air':
    cells.append({'pos':q,'front':front,'states':st.GetBlockStates(q,d),
                  'nbt':b.GetBlockEntityData(d,q)})
_result=json.dumps(cells)''' % (pos,))
            native = execute('''pos=%r
high=(pos[0]+1,pos[1]+1,pos[2])
palette=b.GetBlockPaletteBetweenPos(pos,high,False)
_result=json.dumps({'palette':repr(palette.SerializeBlockPalette()),
 'individual':[bi.GetBlock(pos),bi.GetBlock((pos[0],pos[1]+1,pos[2]))]})''' % (pos,), True)
            result['actors'].append({'name':name,'pos':pos,'use':used,'cells':read,'client':native})
        execute('''from modern_projection.projection.tool_items import SURVEY_WAND
it.SpawnItemToPlayerCarried({'itemName':SURVEY_WAND.encode('utf8'),'count':1,'auxValue':0},p)
_result=True''')
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf8')
    print(json.dumps({'evidence': str(args.output.resolve()),
                      'placements': len(result['placements']), 'actors': len(result['actors'])}))


if __name__ == '__main__':
    main()
