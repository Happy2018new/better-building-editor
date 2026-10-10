"""Probe native snowy overlays in one disposable, empty managed-world cell."""
import json
import math
import mod.server.extraServerApi as api
from modern_projection.projection import block_registry
from modern_projection.server_system import WorldAdapter

factory = api.GetEngineCompFactory()
player = api.GetPlayerList()[0]
dimension = factory.CreateDimension(player).GetEntityDimensionId()
info = factory.CreateBlockInfo(player)
foot = factory.CreatePos(player).GetFootPos()
target = (int(math.floor(foot[0])) + 24, int(math.floor(foot[1])) + 3,
          int(math.floor(foot[2])) - 5)
support = (target[0], target[1] - 1, target[2])
if any(info.GetBlockNew(p, dimension).get('name') != 'minecraft:air'
       for p in (target, support)):
    raise ValueError('Snow overlay export requires an empty disposable area')
adapter = WorldAdapter(player)
results = {}
try:
    adapter.write(support, ('minecraft:dirt', 0))
    for name in sorted(block_registry.BLOCKS):
        basic = info.GetBlockBasicInfo(name.encode('utf8'))
        if not basic or basic.get('renderLayer') != 13:
            continue
        adapter.write(target, ('minecraft:air', 0))
        placed = adapter.write(target, (name, block_registry.DEFAULT_AUX[name]))
        snow = bool(placed and info.SetSnowBlock(target, dimension, 1))
        results[name] = snow
finally:
    adapter.write(target, ('minecraft:air', 0))
    adapter.write(support, ('minecraft:air', 0))
_result = json.dumps({'schema': 1, 'game_version': block_registry.source_version(),
                      'palette_sha256': block_registry.fingerprint(), 'blocks': results},
                     sort_keys=True)
