# -*- coding: utf-8 -*-
"""Probe restoring chest NBT after a one-cell server palette write."""
import json
import math
import mod.server.extraServerApi as serverApi

players = serverApi.GetPlayerList()
if not players:
    _result = {'error': 'no players in the managed test world'}
else:
    player = players[0]
    factory = serverApi.GetEngineCompFactory()
    pos = factory.CreatePos(player).GetPos()
    dimension = factory.CreateDimension(player).GetEntityDimensionId()
    source = (int(math.floor(pos[0])) + 12,
              int(math.floor(pos[1])) - 1,
              int(math.floor(pos[2])))
    target = (source[0] + 1, source[1], source[2])
    info = factory.CreateBlockInfo(serverApi.GetLevelId())
    info.SetBlockNew(source, {'name': 'minecraft:chest', 'aux': 0},
                     0, dimension, True, False)
    original = info.GetBlockEntityData(dimension, source)
    actor = dict(original)
    for axis, delta in (('x', target[0] - source[0]),
                        ('y', target[1] - source[1]),
                        ('z', target[2] - source[2])):
        field = dict(actor[axis])
        field['__value__'] += delta
        actor[axis] = field
    component = factory.CreateBlock(serverApi.GetLevelId())
    palette = component.GetBlankBlockPalette()
    data = {
        'volume': (1, 1, 1),
        'common': {(b'minecraft:chest', 0): [0]},
        'states': {(b'minecraft:chest', 0): {b'minecraft:cardinal_direction': b'south'}},
        'extra': {}, 'extraStates': {}, 'actor': {},
        'void': False, 'eliminateAir': False,
    }
    deserialized = palette.DeserializeBlockPalette(data)
    placed = component.SetBlockByBlockPalette(palette, dimension, target, 0, 0)
    restored = info.SetBlockEntityData(dimension, target, actor)
    result = info.GetBlockEntityData(dimension, target)
    _result = json.dumps({
        'source': source, 'target': target,
        'deserialize': deserialized, 'placed': placed,
        'restored': restored,
        'source_x': original.get('x'), 'target_x': result.get('x') if result else None,
        'id': result.get('id') if result else None,
        'items_type': type(result.get('Items')).__name__ if result else None,
    }, sort_keys=True)
