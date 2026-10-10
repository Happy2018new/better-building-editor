"""Server debug fixture: native player placement on all six support faces.

Run in an owned disposable development world. Read palettes on the client after
replication, then run p0_shulker_orientations_cleanup.py. No NBT setter is used:
SetBlockEntityData facing changes do not guarantee a native rendering change.
"""
import json
import math
import sys
import mod.server.extraServerApi as api

assert not hasattr(sys, '_p0_shulker_faces'), 'Clean up the previous face fixture first'
factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(player)
items = factory.CreateItem(player)
item_type = api.GetMinecraftEnum().ItemPosType.INVENTORY
slot = next((slot for slot in range(36)
             if not items.GetPlayerItem(item_type, slot, True)), None)
assert slot is not None, 'Native face fixture needs one empty inventory slot'
foot = factory.CreatePos(player).GetFootPos()
origin = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 12,
          int(math.floor(foot[2])) + 10)
normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1),
           (-1, 0, 0), (1, 0, 0))
rows = []
for facing, normal in enumerate(normals):
    target = (origin[0] + facing * 3, origin[1], origin[2])
    support = tuple(target[i] - normal[i] for i in range(3))
    for pos in (target, support):
        before = info.GetBlockNew(pos, dimension)
        assert before and before.get('name') == 'minecraft:air', (pos, before)
    rows.append({'support_face': facing, 'pos': target, 'support': support})
sys._p0_shulker_faces = {'schema': 1, 'dimension': dimension, 'rows': rows,
                         'placement': 'PlayerUseItemToPos support face'}
try:
    for row in rows:
        assert info.SetBlockNew(row['support'], {'name': 'minecraft:stone', 'aux': 0},
                                0, dimension, True, False)
        assert items.SpawnItemToPlayerInv({'itemName': 'minecraft:purple_shulker_box',
                                         'count': 1, 'auxValue': 0}, player, slot)
        row['placed'] = info.PlayerUseItemToPos(row['support'], item_type, slot,
                                               row['support_face'])
        row['block'] = info.GetBlockNew(row['pos'], dimension)
        assert row['placed'] and row['block']['name'] == 'minecraft:purple_shulker_box', row
finally:
    assert items.SetInvItemNum(slot, 0), 'Failed to clear the temporary empty-slot item'
_result = json.dumps(sys._p0_shulker_faces)
