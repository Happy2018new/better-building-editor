"""Export engine legacy compatibility, without writing any world blocks.

Run through run_live_check.py against the matching game version. The supplied
palette remains authoritative; aliases may only target records in that file.
"""
import json
import time
from pathlib import Path
import verify_ui as ui
from mcdk import Client, return_value


def server(source):
    with Client() as client:
        return return_value(client.call('execute_code', {'code': source,
            'is_client': False, 'direct_return': True}))


def main():
    path = Path('C:/Users/Happy2018new/AppData/Roaming/MinecraftPE_Netease/logs/block_palette.json')
    records = json.loads(path.read_text(encoding='utf8'))['blocks']
    valid = {(r['name'], r['data']) for r in records}
    names = server('import mod.server.extraServerApi as api\nf=api.GetEngineCompFactory();level=api.GetLevelId()\n_result=f.CreateBlockInfo(level).GetLoadBlocks()')
    # Include archived identifiers even when GetLoadBlocks lists modern names only.
    legacy_names = 'stone dirt sand gravel planks log log2 leaves leaves2 wool concrete concrete_powder stained_glass stained_glass_pane stained_hardened_clay carpet stonebrick grass quartz_block sandstone red_sandstone prismarine sponge wooden_slab double_wooden_slab stone_block_slab stone_block_slab2 stone_block_slab3 stone_block_slab4 double_stone_block_slab double_stone_block_slab2 double_stone_block_slab3 double_stone_block_slab4 red_flower yellow_flower double_plant sapling monster_egg wood anvil purpur_block'.split()
    names = set(names) | {'minecraft:'+n for n in legacy_names}
    queue = sorted((n, d) for n in names if n.startswith('minecraft:') for d in range(16) if (n,d) not in valid)
    result = []
    for start in range(0,len(queue),256):
        rows = server('''import mod.server.extraServerApi as api
f=api.GetEngineCompFactory();level=api.GetLevelId()
item=f.CreateItem(level);state=f.CreateBlockState(level)
rows=[]
for name,aux in '''+repr(queue[start:start+256])+''':
    info=item.GetItemInfoByBlockName(name,aux)
    target=(info or {}).get('newItemName')
    if not target or target==name: continue
    old=state.GetBlockStatesFromAuxValue(name,aux)
    if name in ('minecraft:log','minecraft:log2'):
        old={'pillar_axis':('y','x','z','y')[(aux>>2)&3]}
        if aux&12==12 and target.endswith('_log'): target=target[:-4]+'_wood'
    elif name in ('minecraft:leaves','minecraft:leaves2'):
        old={'persistent_bit':bool(aux&4),'update_bit':bool(aux&8)}
    elif name in ('minecraft:wooden_slab','minecraft:double_wooden_slab') or 'stone_block_slab' in name:
        old={'minecraft:vertical_half':'top' if aux&8 else 'bottom'}
        if name.startswith('minecraft:double_') and target.endswith('_slab'):
            target=target[:-5]+'_double_slab'
    elif name=='minecraft:anvil':
        old={'minecraft:cardinal_direction':('south','west','north','east')[aux&3]}
    elif name in ('minecraft:quartz_block','minecraft:purpur_block') and target.endswith('_pillar'):
        old={'pillar_axis':('y','x','z','y')[(aux>>2)&3]}
    elif name=='minecraft:wood':
        old={'pillar_axis':'y'}
        if aux&8 and not target.startswith('minecraft:stripped_'):
            target='minecraft:stripped_'+target.split(':')[1]
    elif name=='minecraft:sapling':
        old={'age_bit':bool(aux&8)}
    elif name=='minecraft:double_plant':
        old={'upper_block_bit':bool(aux&8)}
    if old is None: continue
    data=state.GetBlockAuxValueFromStates(target,old)
    if data is not None and data>=0: rows.append([name,aux,target,data])
_result=rows''')
        result.extend(row for row in rows if (row[2],row[3]) in valid)
    output = ui.ROOT/'tools/data/legacy_block_aliases.json'
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps({'game':'3.9.0.401155','rows':result},ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'queried':len(queue),'aliases':len(result),'output':str(output)}))


if __name__=='__main__':main()
