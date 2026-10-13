"""Place real private-world frames through SDK item APIs and read typed NBT."""
import json
import time

from capture_native_window import capture
from item_sprite_capture_contract import camera_matches

PREPARE = '''import sys,json
from modern_projection.projection.cell import AIR
from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key
rows=%r
assert not hasattr(sys,'_item_native_reference')
for row in rows:
 for key in ('position','support'):
  assert adapter.read(tuple(row[key]))==AIR
sys._item_native_reference={'changed':[],'rows':rows,'dimension':adapter.dimension}
frames=adapter.factory.CreateBlockEntity(adapter.level)
for row in rows:
 support,position=tuple(row['support']),tuple(row['position'])
 sys._item_native_reference['changed'].append(support)
 assert adapter.write(support,('minecraft:stone',0))
 sys._item_native_reference['changed'].append(position)
 assert adapter.write(position,tuple(row['material']))
 if row['mode']!='empty':
  item={'itemName':'minecraft:diamond_sword','auxValue':0,'count':1,
        'enchantData':[(9,3)] if row['mode']=='enchanted' else []}
  assert frames.SetFrameItem(position,adapter.dimension,item)
  assert frames.SetFrameRotation(position,adapter.dimension,row['rotation'])
observed=[]
for row in rows:
 position=tuple(row['position'])
 item=frames.GetFrameItem(position,adapter.dimension)
 nbt=adapter.info.GetBlockEntityData(adapter.dimension,position)
 root=root_payload(nbt)
 assert root is not None and scalar(root,'id')=='ItemFrame'
 typed_item=root_payload(root.get(field_key(root,'Item')))
 if row['mode']=='empty':
  assert item is None and (typed_item is None or not scalar(typed_item,'Count'))
 else:
  assert item and (item.get('itemName') or item.get('newItemName'))=='minecraft:diamond_sword'
  assert typed_item and scalar(typed_item,'Name')=='minecraft:diamond_sword'
  assert scalar(typed_item,'Damage')==0 and scalar(typed_item,'Count')==1
  tags=root_payload(typed_item.get(field_key(typed_item,'tag'))) or {}
  ench=tags.get(field_key(tags,'ench')) or []
  actual=[(scalar(value,'id'),scalar(value,'lvl')) for value in ench]
  assert actual==([(9,3)] if row['mode']=='enchanted' else [])
  assert scalar(root,'ItemRotation')==row['rotation']
 observed.append({'source':row,'item_api':item,'typed_nbt':nbt})
_result=json.dumps({'kind':'actual native frame blocks','observed':observed,
 'dimension':adapter.dimension,'coordinates_confirmed_air':True,
 'source':'public test.entities.item_contents first frame pair; SetFrameItem diamond sword and ENCHANTMENT(9,3)'})
'''

HIDE = '''import json,sys
frames=adapter.factory.CreateBlockEntity(adapter.level)
for row in sys._item_native_reference['rows']:
 if row['mode']!='empty':
  position=tuple(row['position'])
  assert frames.SetFrameItem(position,adapter.dimension,{'itemName':'minecraft:air','auxValue':0,'count':0})
  assert frames.GetFrameItem(position,adapter.dimension) is None
_result=True
'''

RESTORE = '''import sys
from modern_projection.projection.cell import AIR
saved=sys._item_native_reference
for position in reversed(saved['changed']):
 assert adapter.write(position,AIR)
assert all(adapter.read(position)==AIR for position in saved['changed'])
del sys._item_native_reference
_result=True
'''


def run(check, server, session, closeup, world_capture, state_source, camera_source, folder, wgc, persist):
    reference = {'schema': 1, 'completed': False, 'restored': False, 'captures': [],
                 'lighting': 'Private owned world, frozen clear noon; native materials retain their engine lighting',
                 'routes': ['editor', 'world', 'world_missing', 'native'], 'cleanup_errors': []}
    closeup['native_reference'] = reference
    rows = check.run("from modern_projection.projection.cell import foreground,actor_data\n"
        "from modern_projection.projection.nbt_spatial import root_payload,scalar\n"
        "from modern_projection.projection.visible_actor import entity_nbt\n"
        "positions="+repr(closeup['fixture']['positions'])+"\nrows=[]\n"
        "for mode,local in positions.items():\n"
        " cell=s.editor.document.get(tuple(local))\n"
        " position=tuple(s.origin[axis]+local[axis] for axis in range(3))\n"
        " rows.append({'mode':mode,'position':position,'support':(position[0],position[1],position[2]+1),"
        "'material':foreground(cell),'rotation':scalar(root_payload(entity_nbt(actor_data(cell))),'ItemRotation') or 0.})\n"
        "_result=rows")
    for index in range(20):
        time.sleep(.4)
        world_capture('world_missing_'+str(index))
    check.run('b.stop_projection()\n_result=True')
    initialized = False
    try:
        # Mark pending before the call: it may partially mutate and fail.
        initialized = True
        result = server(PREPARE % rows)
        reference['placement'] = json.loads(result) if isinstance(result, str) else result
        persist()
        check.wait('native frames replicated to client', lambda value: value is True,
            lambda: check.run("info=b.factory.CreateBlockInfo(b.level)\npositions="+repr(rows)+"\n"
                "_result=all(info.GetBlockEntityData(tuple(row['position'])) is not None for row in positions)"))
        time.sleep(1.)
        def sample(label):
            before = check.run(camera_source)
            image = capture(session['session_file'], session['owner'], folder/(label+'.png'), wgc)
            after = check.run(camera_source)
            assert camera_matches(before, closeup['world_camera']) and camera_matches(after, closeup['world_camera'])
            reference['captures'].append({'label': label, 'capture': image,
                'camera_before': before, 'camera_after': after, 'camera_expected': closeup['world_camera']})
            persist()
        for index in range(20):
            time.sleep(.4)
            sample('native_'+str(index))
        reference['hidden_readback'] = server(HIDE)
        time.sleep(1.)
        sample('native_items_hidden')
        reference['completed'] = True
    finally:
        if initialized:
            try:
                reference['restored'] = bool(server(RESTORE))
            except Exception as error:
                reference['cleanup_errors'].append(type(error).__name__+': '+str(error))
        persist()
    if reference['cleanup_errors']:
        raise RuntimeError('Native frame restore failed')
    return reference
