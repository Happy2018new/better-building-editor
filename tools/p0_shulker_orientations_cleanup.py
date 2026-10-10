"""Remove the debug-only native face fixtures recorded by the setup helper."""
import sys
import mod.server.extraServerApi as api

saved = sys._p0_shulker_faces
info = api.GetEngineCompFactory().CreateBlockInfo(api.GetPlayerList()[0])
failures = []
for row in saved['rows']:
    for pos in (row['pos'], row['support']):
        if not info.SetBlockNew(tuple(pos), {'name': 'minecraft:air', 'aux': 0},
                                0, saved['dimension'], True, False):
            failures.append(pos)
assert not failures, ('Native fixture cleanup failed', failures)
del sys._p0_shulker_faces
_result = True
