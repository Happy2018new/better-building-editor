"""Remove the debug-only native face fixtures recorded by the setup helper."""
import sys
import mod.server.extraServerApi as api

saved = sys._p0_shulker_faces
factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
info = factory.CreateBlockInfo(player)
failures = []
for row in saved['rows']:
    for pos in (row['pos'], row['support']):
        info.SetBlockNew(tuple(pos), {'name': 'minecraft:air', 'aux': 0},
                         0, saved['dimension'], True, False)
        actual = info.GetBlockNew(tuple(pos), saved['dimension'])
        if not actual or actual.get('name') != 'minecraft:air':
            failures.append(pos)
if 'slot' in saved:
    items = factory.CreateItem(player)
    items.SetInvItemNum(saved['slot'], 0)
    remaining = items.GetPlayerItem(api.GetMinecraftEnum().ItemPosType.INVENTORY,
                                   saved['slot'], True)
    assert not remaining or not remaining.get('count'), ('Native fixture item cleanup failed', remaining)
assert not failures, ('Native fixture cleanup failed', failures)
del sys._p0_shulker_faces
_result = True
