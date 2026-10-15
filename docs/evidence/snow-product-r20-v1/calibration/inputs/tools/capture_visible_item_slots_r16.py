"""Observe real item-use slot payloads in one restored private-world fixture."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'.agents/skills/pyreact-debugging/scripts'))
from mcdk import Client, return_value
from _session import load_session

PREPARE = '''import sys,json
import mod.server.extraServerApi as slot_api
from modern_projection.server_system import WorldAdapter as SlotWorldAdapter
from modern_projection.projection.cell import AIR as SLOT_AIR
assert len(slot_api.GetPlayerList())==1
assert slot_api.GetMinecraftVersion()=='1.21.130.0'
slot_player=slot_api.GetPlayerList()[0]
slot_adapter=SlotWorldAdapter(slot_player)
slot_foot=slot_adapter.factory.CreatePos(slot_player).GetFootPos()
assert slot_foot[1]>-128, slot_foot
assert not hasattr(sys,'_visible_item_slot_fixture_r16')
slot_origin=(int(slot_foot[0])+6,int(slot_foot[1])+3,int(slot_foot[2])+6)
slot_rows=[{'name':name,'pos':(slot_origin[0]+index*4,slot_origin[1],slot_origin[2]),
            'item':item,'count':count,'facing':3 if name=='minecraft:oak_shelf' else 2}
           for index,(name,item,count) in enumerate((
            ('minecraft:oak_shelf','minecraft:diamond_sword',3),
            ('minecraft:campfire','minecraft:beef',4),
            ('minecraft:lectern','minecraft:writable_book',1)))]
slot_items=slot_adapter.factory.CreateItem(slot_player)
slot_inventory_type=slot_api.GetMinecraftEnum().ItemPosType.INVENTORY
slot_empty=next((index for index in range(36) if not slot_items.GetPlayerItem(slot_inventory_type,index,True)
             or not slot_items.GetPlayerItem(slot_inventory_type,index,True).get('count')),None)
assert slot_empty is not None
slot_cells=[]
for row in slot_rows:
 for shift in ((0,0,0),(0,-1,0)):
  pos=tuple(row['pos'][axis]+shift[axis] for axis in range(3))
  assert slot_adapter.read(pos)==SLOT_AIR, (pos,slot_adapter.read(pos))
  slot_cells.append(pos)
sys._visible_item_slot_fixture_r16={'rows':slot_rows,'changed':[],
 'slot':slot_empty,'rotation':slot_adapter.factory.CreateRot(slot_player).GetRot(),
 'player':slot_player,'dimension':slot_adapter.dimension}
for row in slot_rows:
 support=(row['pos'][0],row['pos'][1]-1,row['pos'][2])
 sys._visible_item_slot_fixture_r16['changed'].append(support)
 assert slot_adapter.write(support,('minecraft:stone',0))
 sys._visible_item_slot_fixture_r16['changed'].append(row['pos'])
 assert slot_adapter.write(row['pos'],(row['name'],0))
 row['before']=slot_adapter.info.GetBlockEntityData(slot_adapter.dimension,row['pos'])
_result=slot_rows
'''
USE = '''import sys
saved=sys._visible_item_slot_fixture_r16
row=saved['rows'][%d]
items=slot_adapter.factory.CreateItem(saved['player'])
info=slot_adapter.factory.CreateBlockInfo(saved['player'])
assert items.SetInvItemNum(saved['slot'],0)
assert items.SpawnItemToPlayerInv({'itemName':row['item'],'auxValue':0,'count':row['count']},saved['player'],saved['slot'])
if row['item']=='minecraft:diamond_sword':assert items.AddEnchantToInvItem(saved['slot'],9,3)
used=[]
for index in range(row['count']):
 used.append(info.PlayerUseItemToPos(row['pos'],slot_inventory_type,saved['slot'],row['facing']))
row['uses']=used
row['after']=slot_adapter.info.GetBlockEntityData(saved['dimension'],row['pos'])
row['block']=slot_adapter.info.GetBlockNew(row['pos'],saved['dimension'])
assert items.SetInvItemNum(saved['slot'],0)
_result=row
'''
RESTORE = '''import sys
saved=getattr(sys,'_visible_item_slot_fixture_r16',None)
if saved is None:_result={'restored':True,'owned':False}
else:
 items=slot_adapter.factory.CreateItem(saved['player'])
 assert items.SetInvItemNum(saved['slot'],0)
 errors=[]
 for pos in reversed(saved['changed']):
  slot_adapter.write(pos,SLOT_AIR)
  if slot_adapter.read(pos)!=SLOT_AIR:errors.append(pos)
 _result={'restored':not errors,'errors':errors}
 if not errors:del sys._visible_item_slot_fixture_r16
'''

PALETTE = '''import mod.client.extraClientApi as slot_client_api
slot_position=%r
slot_factory=slot_client_api.GetEngineCompFactory()
slot_palette=slot_factory.CreateBlock(slot_client_api.GetLevelId()).GetBlockPaletteBetweenPos(slot_position,slot_position,False)
assert slot_palette is not None
slot_raw=slot_palette.SerializeBlockPalette()
slot_actors=[{'name':name,'actor':entries.get(0)} for name,entries in slot_raw.get('actor',{}).items()]
_result={'engine':slot_client_api.GetEngineVersion(),'volume':slot_raw['volume'],
 'common':[(value,indices) for value,indices in slot_raw.get('common',{}).items()],
 'actors':slot_actors}
'''


def run(session, owner, output):
    os.environ.update(MCDEV_SESSION_FILE=str(session), MCDEV_OWNER=owner,
                      MCDEV_ALLOW_USER_FOREGROUND='1')
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Preserve previous observation output')
    report = {'schema': 1, 'owner': owner, 'observations': [],
              'source': 'Public captured-default NBT names with real native item use',
              'production_qualified': False}
    manifest = load_session(session, owner, live=True)
    report['engine_version'] = Path(manifest['game_executable']).parent.name
    report['session_id'] = manifest['id']
    report['session_manifest_sha256'] = hashlib.sha256(session.read_bytes()).hexdigest()
    def save():
        output.write_text(json.dumps(report, ensure_ascii=True, indent=2)+'\n', encoding='ascii')
    with Client(timeout=20) as client:
        def execute(code, server=True):
            result = client.call('execute_code', {'code': code, 'is_client': not server,
                                                  'direct_return': True})
            if result.get('isError'):
                raise RuntimeError(result)
            return return_value(result)
        try:
            report['native_runtime_version'] = execute('import mod.server.extraServerApi as slot_version_api\n'
                                                     '_result=slot_version_api.GetMinecraftVersion()\n')
            report['prepared'] = execute(PREPARE)
            save()
            time.sleep(1.)
            for index, row in enumerate(report['prepared']):
                position = tuple(row['pos'])
                client_state = execute('import mod.client.extraClientApi as slot_client_api\n'
                    'slot_client_info=slot_client_api.GetEngineCompFactory().CreateBlockInfo(slot_client_api.GetLevelId())\n'
                    '_result=slot_client_info.GetBlock('+repr(position)+')\n', False)
                report.setdefault('client_readbacks', []).append(client_state)
                client_name = (client_state.get('name') if isinstance(client_state, dict) else
                               client_state[0] if isinstance(client_state, (list, tuple)) and client_state else None)
                if client_name != row['name']:
                    raise ValueError('Native slot fixture did not reach the client: '+repr(client_state))
                before_palette=execute(PALETTE % (position,),False)
                observed = execute(USE % index)
                observed['client_before']=before_palette
                time.sleep(.4)
                observed['client_after']=execute(PALETTE % (position,),False)
                report['observations'].append(observed)
                save()
            report['completed'] = True
        except Exception as error:
            report['error'] = type(error).__name__+': '+str(error)
            raise
        finally:
            report['restoration'] = execute(RESTORE)
            save()
    print(json.dumps({'output': str(output), 'completed': report.get('completed'),
                      'restored': report['restoration']['restored']}))


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--owner',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    run(args.session,args.owner,args.output)
