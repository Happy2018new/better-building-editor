# -*- coding: utf-8 -*-
"""One-shot server probe for complete native block palette serialization."""
import json
import math
import mod.server.extraServerApi as serverApi

player_ids = serverApi.GetPlayerList()
if not player_ids:
    _result = {'error': 'no players in the managed test world'}
else:
    player_id = player_ids[0]
    factory = serverApi.GetEngineCompFactory()
    pos = factory.CreatePos(player_id).GetPos()
    dimension = factory.CreateDimension(player_id).GetEntityDimensionId()
    base = (int(math.floor(pos[0])), int(math.floor(pos[1])) - 1,
            int(math.floor(pos[2])))
    points = {
        'waterlogged_stairs': (base[0] + 2, base[1], base[2]),
        'snow_cover': (base[0] + 3, base[1], base[2]),
        'snow_layer_above': (base[0] + 3, base[1] + 1, base[2]),
        'chest': (base[0] + 4, base[1], base[2]),
    }

    block_info = factory.CreateBlockInfo(player_id)
    write_results = {
        'waterlogged_stairs': block_info.SetBlockNew(
            points['waterlogged_stairs'],
            {'name': 'minecraft:oak_stairs', 'aux': 0}, 0, dimension, True, False),
        'liquid': block_info.SetLiquidBlock(
            points['waterlogged_stairs'],
            {'name': 'minecraft:water', 'aux': 0}, dimension),
        'snow_base': block_info.SetBlockNew(
            points['snow_cover'],
            {'name': 'minecraft:oak_leaves', 'aux': 0}, 0, dimension, True, False),
        'snow': block_info.SetSnowBlock(points['snow_cover'], dimension, 1),
        'snow_above': block_info.SetSnowBlock(
            points['snow_layer_above'], dimension, 1),
        'chest': block_info.SetBlockNew(
            points['chest'],
            {'name': 'minecraft:chest', 'aux': 0}, 0, dimension, True, False),
    }
    actor_data = block_info.GetBlockEntityData(dimension, points['chest'])
    block_values = dict((name, {
        'front': block_info.GetBlockNew(pos, dimension),
        'liquid': block_info.GetLiquidBlock(pos, dimension),
    }) for name, pos in points.items())

    low = tuple(min(base[i] + 2, base[i] + 4) for i in range(3))
    high = tuple(max(base[i] + 2, base[i] + 4) for i in range(3))
    high = (high[0] + 1, high[1] + 1, high[2] + 1)
    level_id = serverApi.GetLevelId()
    block_components = {
        'level': factory.CreateBlock(level_id),
        'player': factory.CreateBlock(player_id),
    }
    bounds = (low, high)
    results = {}
    for label, component in block_components.items():
        palette = component.GetBlockPaletteBetweenPos(
            dimension, bounds[0], bounds[1])
        results[label] = {
            'component_type': type(component).__name__,
            'palette_is_none': palette is None,
            'methods': [name for name in dir(component)
                        if 'Palette' in name or 'Block' in name],
        }
        if palette is not None:
            serialized = palette.SerializeBlockPalette()
            results[label]['palette_keys'] = sorted(serialized.keys())
            results[label]['palette'] = serialized
    _result = json.dumps({
        'game': 'NEMC 3.9.0.401155',
        'dimension': dimension,
        'origin': base,
        'positions': points,
        'write_results': write_results,
        'block_values': block_values,
        'actor_data_type': type(actor_data).__name__,
        'actor_data': actor_data,
        'results': results,
    }, sort_keys=True)
