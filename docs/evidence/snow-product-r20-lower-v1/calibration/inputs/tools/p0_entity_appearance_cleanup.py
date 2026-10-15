"""Restore all temporary native appearance fixture cells, rotation and inventory."""
import sys
import mod.server.extraServerApi as api

saved = sys._p0_entity_appearances
factory = api.GetEngineCompFactory()
info = factory.CreateBlockInfo(saved['player'])
errors = []
for unused in range(2):
    for pos in saved['reserved']:
        try:
            info.SetBlockNew(tuple(pos), {'name': 'minecraft:air', 'aux': 0},
                             0, saved['dimension'], False, False)
        except Exception as error:
            errors.append(('world_write', pos, str(error)))
for pos in saved['reserved']:
    try:
        actual = info.GetBlockNew(tuple(pos), saved['dimension'])
        if not actual or actual.get('name') != 'minecraft:air':
            errors.append(('world', pos, actual))
    except Exception as error:
        errors.append(('world_read', pos, str(error)))
try:
    items = factory.CreateItem(saved['player'])
    items.SetInvItemNum(saved['slot'], 0)
    remaining = items.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.INVENTORY, saved['slot'], True)
    if remaining and remaining.get('count'):
        errors.append(('inventory', remaining))
except Exception as error:
    errors.append(('inventory', str(error)))
try:
    if not factory.CreateRot(saved['player']).SetRot(tuple(saved['rotation'])):
        errors.append(('player_rotation', saved['rotation']))
except Exception as error:
    errors.append(('player_rotation', str(error)))
saved['cleanup_errors'] = errors
assert not errors, ('Native appearance cleanup failed', errors)
del sys._p0_entity_appearances
_result = True
