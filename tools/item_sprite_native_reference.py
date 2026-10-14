"""Place real private-world frames through SDK item APIs and read typed NBT."""
import json
import time

from capture_native_window import capture
from item_sprite_capture_contract import camera_matches

PREPARE = '''import sys,json
from modern_projection.projection.cell import AIR
from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key
rows=%r
platform=%r
assert not hasattr(sys,'_item_native_reference')
for row in rows:
 for key in ('position','support'):
  assert adapter.read(tuple(row[key]))==AIR
if platform is not None:
 assert adapter.read(tuple(platform))==AIR
items=adapter.factory.CreateItem(players[0])
player_info=adapter.factory.CreateBlockInfo(players[0])
rot=adapter.factory.CreateRot(players[0])
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=next((index for index in range(36) if not items.GetPlayerItem(item_type,index,True)
           or not items.GetPlayerItem(item_type,index,True).get('count')),None)
assert slot is not None
sys._item_native_reference={'changed':[],'rows':rows,'dimension':adapter.dimension,
 'slot':slot,'rotation':rot.GetRot()}
if platform is not None:
 pos=adapter.factory.CreatePos(players[0])
 sys._item_native_reference['foot_before']=pos.GetFootPos()
 sys._item_native_reference['changed'].append(tuple(platform))
 wrote=adapter.write(tuple(platform),('minecraft:stone',0))
 assert adapter.read(tuple(platform))==('minecraft:stone',0)
 foot=(platform[0]+.5,platform[1]+1.,platform[2]+.5)
 assert pos.SetFootPos(foot)
 actual=pos.GetFootPos()
 assert max(abs(actual[axis]-foot[axis]) for axis in range(3))<.002
 sys._item_native_reference['player_placement']={'platform':platform,'write_return':wrote,
  'foot_before':sys._item_native_reference['foot_before'],'foot_during':actual}
assert rot.SetRot((0.,0.))
for row in rows:
 support,position=tuple(row['support']),tuple(row['position'])
 sys._item_native_reference['changed'].append(support)
 assert adapter.write(support,('minecraft:stone',0))
 sys._item_native_reference['changed'].append(position)
 assert items.SetInvItemNum(slot,0)
 assert items.SpawnItemToPlayerInv({'itemName':row.get('frame_name','minecraft:frame'),'auxValue':0,'count':1},players[0],slot)
 assert player_info.PlayerUseItemToPos(support,item_type,slot,row.get('face',2))
 actual=adapter.read(position)
 assert actual[0]==row.get('frame_name','minecraft:frame')
 row['placed_material']=actual
 row['placed_block']=adapter.info.GetBlockNew(position,adapter.dimension)
assert items.SetInvItemNum(slot,0)
assert rot.SetRot(sys._item_native_reference['rotation'])
_result=json.dumps({'rows':rows,'slot':slot,'coordinates_confirmed_air':True,
 'placement':'native PlayerUseItemToPos on support face2',
 'player_placement':sys._item_native_reference.get('player_placement')})
'''

FILL = '''import sys,json
from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key
saved=sys._item_native_reference
rows=saved['rows']
items=adapter.factory.CreateItem(players[0])
player_info=adapter.factory.CreateBlockInfo(players[0])
frames=adapter.factory.CreateBlockEntity(adapter.level)
item_type=api.GetMinecraftEnum().ItemPosType.INVENTORY
slot=saved['slot']
for row in rows:
 position=tuple(row['position'])
 if row['mode']!='empty':
  assert items.SetInvItemNum(slot,0)
  assert items.SpawnItemToPlayerInv({'itemName':'minecraft:diamond_sword','auxValue':0,'count':1},players[0],slot)
  if row['mode']=='enchanted':
   assert items.AddEnchantToInvItem(slot,9,3)
  assert tuple(map(tuple,items.GetInvItemEnchantData(slot) or ()))==(((9,3),) if row['mode']=='enchanted' else ())
  assert player_info.PlayerUseItemToPos(position,item_type,slot,row.get('face',2))
  row['item_write_route']='native inventory PlayerUseItemToPos only; no subsequent frame setters'
  if row['rotation']:
   assert frames.SetFrameRotation(position,adapter.dimension,row['rotation'])
   row['rotation_write_route']='native SetFrameRotation after item insertion'
assert items.SetInvItemNum(slot,0)
observed=[]
for row in rows:
 position=tuple(row['position'])
 item=frames.GetFrameItem(position,adapter.dimension)
 nbt=adapter.info.GetBlockEntityData(adapter.dimension,position)
 root=root_payload(nbt)
 assert root is not None and scalar(root,'id')==('GlowItemFrame' if row.get('frame_name')=='minecraft:glow_frame' else 'ItemFrame')
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
 'source':'public test.entities.item_contents first frame pair; actual native frame and inventory diamond sword interaction; AddEnchantToInvItem(9,3), no subsequent frame setters'})
'''

HIDE_CLEAR = '''import sys
from modern_projection.projection.cell import AIR
for row in sys._item_native_reference['rows']:
 if row['mode']!='empty':
  assert adapter.write(tuple(row['position']),AIR)
_result=True
'''

HIDE_PLACE = '''import sys
saved=sys._item_native_reference
items=adapter.factory.CreateItem(players[0])
info=adapter.factory.CreateBlockInfo(players[0])
rot=adapter.factory.CreateRot(players[0])
assert rot.SetRot((0.,0.))
for row in saved['rows']:
 if row['mode']!='empty':
  assert items.SetInvItemNum(saved['slot'],0)
  assert items.SpawnItemToPlayerInv({'itemName':row.get('frame_name','minecraft:frame'),'auxValue':0,'count':1},players[0],saved['slot'])
  assert info.PlayerUseItemToPos(tuple(row['support']),api.GetMinecraftEnum().ItemPosType.INVENTORY,saved['slot'],row.get('face',2))
assert items.SetInvItemNum(saved['slot'],0)
assert rot.SetRot(saved['rotation'])
_result=True
'''

RESTORE = '''import sys
from modern_projection.projection.cell import AIR
saved=sys._item_native_reference
items=adapter.factory.CreateItem(players[0])
rot=adapter.factory.CreateRot(players[0])
assert items.SetInvItemNum(saved['slot'],0)
assert rot.SetRot(saved['rotation'])
foot_restore=None
if 'foot_before' in saved:
 pos=adapter.factory.CreatePos(players[0])
 requested=tuple(saved['foot_before'])
 returned=pos.SetFootPos(requested)
 actual=pos.GetFootPos()
 foot_restore={'requested':requested,'actual':actual,'return':returned,
  'passed':max(abs(actual[axis]-requested[axis]) for axis in range(3))<.002}
results=[]
for position in reversed(saved['changed']):
 wrote=adapter.write(position,AIR)
 actual=adapter.read(position)
 results.append({'position':position,'write_return':wrote,'actual':actual,'passed':actual==AIR})
assert all(row['passed'] for row in results),results
assert foot_restore is None or foot_restore['passed'],foot_restore
del sys._item_native_reference
_result={'passed':True,'rows':results,'player_foot':foot_restore}
'''


def run(check, server, session, closeup, world_capture, state_source, camera_source, folder, wgc, persist,
        native_player_near=False):
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
    distances = "info=b.factory.CreateBlockInfo(b.level)\nrender=b.factory.CreateActorRender(b.player)\n" \
        "_result={'block':info.GetBlockRenderDistance(),'entity':render.GetEntityRenderDistance()," \
        "'projection_lease':b.projection_distance,'foot':b.player_origin()}"
    reference['render_distances_before_stop'] = check.run(distances)
    check.run('b.stop_projection()\n_result=True')
    reference['render_distances_after_stop'] = check.run(distances)
    persist()
    initialized = False
    try:
        # Mark pending before the call: it may partially mutate and fail.
        initialized = True
        platform = None
        if native_player_near:
            import math
            platform = (int(math.floor(closeup['world_camera']['position'][0])),
                        rows[0]['position'][1]-1, rows[0]['position'][2]-4)
        reference['declared_player_platform'] = platform
        result = server(PREPARE % (rows, platform))
        reference['frame_setup'] = json.loads(result) if isinstance(result, str) else result
        if native_player_near:
            # Teleport can reset a departed camera; reapply only its declared pose.
            check.run("cam=b.factory.CreateCamera(b.level)\ncam.DepartCamera()\n"
                "assert cam.SetCameraPos(%r)\nassert cam.SetCameraRotation(%r)\n_result=True" %
                (tuple(closeup['world_camera']['position']),tuple(closeup['world_camera']['rotation'])))
            check.wait('declared native near-player camera',
                lambda value:camera_matches(value,closeup['world_camera']),lambda:check.run(camera_source))
        persist()
        check.wait('native frames replicated to client', lambda value: value is True,
            lambda: check.run("info=b.factory.CreateBlockInfo(b.level)\npositions="+repr(rows)+"\n"
                "_result=all(info.GetBlockEntityData(tuple(row['position'])) is not None for row in positions)"))
        def sample(label):
            before = check.run(camera_source)
            image = capture(session['session_file'], session['owner'], folder/(label+'.png'), wgc)
            after = check.run(camera_source)
            assert camera_matches(before, closeup['world_camera']) and camera_matches(after, closeup['world_camera'])
            reference['captures'].append({'label': label, 'capture': image,
                'camera_before': before, 'camera_after': after, 'camera_expected': closeup['world_camera']})
            persist()
        sample('native_before_fill')
        result = server(FILL)
        reference['placement'] = json.loads(result) if isinstance(result,str) else result
        client_read = "from modern_projection.projection.nbt_spatial import root_payload,scalar,field_key\n" \
            "info=b.factory.CreateBlockInfo(b.level)\npositions="+repr(rows)+"\nobserved=[]\n" \
            "for row in positions:\n" \
            " root=root_payload(info.GetBlockEntityData(tuple(row['position'])))\n" \
            " item=root_payload(root.get(field_key(root,'Item'))) if root else None\n" \
            " tags=root_payload(item.get(field_key(item,'tag'))) if item else None\n" \
            " ench=tags.get(field_key(tags,'ench')) if tags else None\n" \
            " actual=[(scalar(value,'id'),scalar(value,'lvl')) for value in (ench or ())]\n" \
            " passed=(bool(root) and (not item or not scalar(item,'Count'))) if row['mode']=='empty' else " \
            "(bool(item) and scalar(item,'Name')=='minecraft:diamond_sword' and scalar(item,'Count')==1 " \
            "and actual==([(9,3)] if row['mode']=='enchanted' else []))\n" \
            " observed.append({'source':row,'typed_nbt':root,'passed':passed})\n" \
            "_result={'passed':all(row['passed'] for row in observed),'rows':observed}"
        reference['client_item_readback'] = check.wait('actual native client typed items',
            lambda value:value['passed'],lambda:check.run(client_read))
        persist()
        for index in range(20):
            time.sleep(.4)
            sample('native_'+str(index))
        reference['hidden_clear'] = server(HIDE_CLEAR)
        check.wait('native hidden frame cells replicated air',lambda value:value is True,
            lambda:check.run("info=b.factory.CreateBlockInfo(b.level)\npositions="+repr(rows)+"\n"
                "_result=all(info.GetBlock(tuple(row['position']))[0]=='minecraft:air' "
                "for row in positions if row['mode']!='empty')"))
        reference['hidden_readback'] = server(HIDE_PLACE)
        check.wait('native recreated empty frames replicated',lambda value:value is True,
            lambda:check.run("from modern_projection.projection.nbt_spatial import root_payload,field_key,scalar\n"
                "info=b.factory.CreateBlockInfo(b.level)\npositions="+repr(rows)+"\nvalid=[]\n"
                "for row in positions:\n"
                " root=root_payload(info.GetBlockEntityData(tuple(row['position'])))\n"
                " item=root_payload(root.get(field_key(root,'Item'))) if root else None\n"
                " valid.append(bool(root) and (not item or not scalar(item,'Count')))\n"
                "_result=all(valid)"))
        sample('native_items_hidden')
        reference['completed'] = True
    finally:
        if initialized:
            try:
                reference['restoration'] = server(RESTORE)
                reference['restored'] = reference['restoration'].get('passed') is True
            except Exception as error:
                reference['cleanup_errors'].append(type(error).__name__+': '+str(error))
        persist()
    if reference['cleanup_errors']:
        raise RuntimeError('Native frame restore failed')
    return reference
