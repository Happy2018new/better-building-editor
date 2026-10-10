"""Restore all temporary native appearance fixture cells, rotation and inventory."""
import sys
import mod.server.extraServerApi as api

saved = sys._p0_entity_appearances
factory = api.GetEngineCompFactory()
info = factory.CreateBlockInfo(saved['player'])
errors = []
for unused in range(2):
    for pos in saved['reserved']:
        info.SetBlockNew(tuple(pos), {'name': 'minecraft:air', 'aux': 0},
                         0, saved['dimension'], False, False)
for pos in saved['reserved']:
    actual = info.GetBlockNew(tuple(pos), saved['dimension'])
    if not actual or actual.get('name') != 'minecraft:air':
        errors.append(('world', pos, actual))
items = factory.CreateItem(saved['player'])
items.SetInvItemNum(saved['slot'], 0)
remaining = items.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.INVENTORY, saved['slot'], True)
if remaining and remaining.get('count'):
    errors.append(('inventory', remaining))
if not factory.CreateRot(saved['player']).SetRot(tuple(saved['rotation'])):
    errors.append(('player_rotation', saved['rotation']))
assert not errors, ('Native appearance cleanup failed', errors)
del sys._p0_entity_appearances
_result = True
