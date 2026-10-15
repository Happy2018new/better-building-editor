# -*- coding: utf-8 -*-
"""Probe one-cell server palette write for a waterlogged stair."""
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
    target = (int(math.floor(pos[0])) + 8,
              int(math.floor(pos[1])) - 1,
              int(math.floor(pos[2])))
    component = factory.CreateBlock(serverApi.GetLevelId())
    palette = component.GetBlankBlockPalette()
    data = {
        'volume': (1, 1, 1),
        'common': {(b'minecraft:oak_stairs', 0): [0]},
        'states': {(b'minecraft:oak_stairs', 0): {
            b'weirdo_direction': 0, b'upside_down_bit': False}},
        'extra': {(b'minecraft:water', 0): [0]},
        'extraStates': {(b'minecraft:water', 0): {b'liquid_depth': 0}},
        'actor': {}, 'void': False, 'eliminateAir': False,
    }
    deserialized = palette.DeserializeBlockPalette(data)
    result = component.SetBlockByBlockPalette(palette, dimension, target, 0, 0)
    info = factory.CreateBlockInfo(serverApi.GetLevelId())
    _result = json.dumps({
        'target': target,
        'deserialize': deserialized,
        'write': result,
        'front': info.GetBlockNew(target, dimension),
        'liquid': info.GetLiquidBlock(target, dimension),
    }, sort_keys=True)
