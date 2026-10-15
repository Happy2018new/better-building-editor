"""Observe genuinely item-placed heads in the assigned production world.

Source cells must be empty, including extra blocks. Inventory and fixture
changes are journaled and restored explicitly. All runtime calls are bound
to the supplied instance; screenshots use background WGC.
"""
import argparse
import json
import os
from pathlib import Path
import time

import audit_native_visual_r15 as native
from capture_native_window import capture
from verify_debug_blueprints import CLIENT

ORIGIN = (0, -56, 20)
NAMES = ('piglin_head', 'player_head', 'skeleton_skull', 'dragon_head')
PREFIX = CLIENT + "system=owner\nfactory=getattr(sys,'_native_r15_factory',b.factory)\nlevel=b.level\n"
SERVER = native.SERVER

ADMISSION = PREFIX + '''if s.projection_active:b.stop_projection()
if navigator.top is not None:navigator.pop()
palette=b.factory.CreateBlock(b.level).GetBlockPaletteBetweenPos((0,-57,20),(9,-55,21),False)
raw=palette.SerializeBlockPalette()
assert not raw.get('extra'),raw.get('extra')
_result=json.dumps({'engine':api.GetEngineVersion(),'extra':str(raw.get('extra')),
 'common':str(raw.get('common'))})
'''

SETUP = SERVER + '''assert not hasattr(api,'_native_head_items'), 'Restore previous fixture first'
origin=%r
names=%r
saved={'journal':[],'rows':[],'origin':origin}
api._native_head_items=saved
items=factory.CreateItem(player)
slot=35
inventory_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
original=items.GetPlayerItem(inventory_type,slot,True)
try:
 for index,name in enumerate(names):
  pos=(origin[0]+index*3,origin[1],origin[2])
  support=(pos[0],pos[1]-1,pos[2])
  assert info.GetBlockNew(pos,dimension)['name']=='minecraft:air'
  for target in (support,pos):
   saved['journal'].append({'pos':target,'block':info.GetBlockNew(target,dimension),
    'nbt':info.GetBlockEntityData(dimension,target)})
  assert info.SetBlockNew(support,{'name':'minecraft:stone','aux':0},0,dimension,True,False)
  items.SetInvItemNum(slot,0)
  spawned=items.SpawnItemToPlayerInv({'itemName':'minecraft:'+name,'count':1,'auxValue':0},player,slot)
  used=info.PlayerUseItemToPos(support,inventory_type,slot,1)
  row={'name':'minecraft:'+name,'pos':pos,'spawned':spawned,'used':used,
   'actual':info.GetBlockNew(pos,dimension),'states':state.GetBlockStates(pos,dimension),
   'nbt':info.GetBlockEntityData(dimension,pos)}
  saved['rows'].append(row)
finally:
 items.SetInvItemNum(slot,0)
 if original:items.SpawnItemToPlayerInv(original,player,slot)
_result=json.dumps({'rows':saved['rows'],
 'inventory_restored':items.GetPlayerItem(inventory_type,slot,True)==original})
'''

READ = SERVER + '''_result=json.dumps({'rows':[dict(row,
 actual=info.GetBlockNew(row['pos'],dimension),states=state.GetBlockStates(row['pos'],dimension),
 nbt=info.GetBlockEntityData(dimension,row['pos'])) for row in api._native_head_items['rows']]})
'''

RAW = native.PROJECT.replace(native.CLIENT, PREFIX, 1).replace(
    'raw=palette.SerializeBlockPalette()',
    "raw=palette.SerializeBlockPalette()\nassert not raw.get('extra'),raw.get('extra')")
CAMERA = native.CAMERA.replace(native.CLIENT, PREFIX, 1)
STATE = native.STATE.replace(native.CLIENT, PREFIX, 1).replace(
    'system.render_ticks', "getattr(system,'render_ticks',None)")
RESTORE = SERVER + '''saved=api._native_head_items
for entry in reversed(saved['journal']):
 info.SetBlockNew(entry['pos'],entry['block'],0,dimension,True,False)
 if entry['nbt']:info.SetBlockEntityData(dimension,entry['pos'],entry['nbt'])
del api._native_head_items
_result=True
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('setup', 'read', 'raw', 'camera', 'capture',
                                         'hide', 'restore'))
    parser.add_argument('--session', required=True)
    parser.add_argument('--owner', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    audit = native.Audit(args)
    audit.env = dict(os.environ)
    report = {'action': args.action, 'session': args.session, 'owner': args.owner,
              'manual_pixel_acceptance': False}
    if args.action == 'setup':
        report['admission'] = audit.execute('admission', ADMISSION)
        report['result'] = audit.execute('setup', SETUP % (ORIGIN, NAMES), False)
    elif args.action == 'read':
        report['result'] = audit.execute('read', READ, False)
    elif args.action == 'raw':
        rows = [{'name': 'minecraft:' + name} for name in NAMES]
        report['result'] = audit.execute('raw', RAW % (ORIGIN, rows, 'r15_item_heads_%d' % time.time_ns()))
    elif args.action == 'camera':
        report['result'] = audit.execute('camera', CAMERA)
    elif args.action == 'hide':
        report['result'] = audit.execute('hide', native.HIDE.replace(native.CLIENT, PREFIX, 1) % True)
    elif args.action == 'restore':
        report['client'] = audit.execute('restore_client', native.RESTORE_CLIENT.replace(native.CLIENT, PREFIX, 1))
        report['server'] = audit.execute('restore_server', RESTORE, False)
    else:
        report['before'] = audit.execute('before', STATE)
        report['capture'] = capture(args.session, args.owner, args.output / 'frame.png', native.WGC)
        report['after'] = audit.execute('after', STATE)
    native.save(args.output / 'report.json', report)
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
