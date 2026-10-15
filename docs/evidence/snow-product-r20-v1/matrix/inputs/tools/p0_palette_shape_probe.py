# -*- coding: utf-8 -*-
"""Read the server-side blank palette serialization for one-cell writes."""
import json
import mod.server.extraServerApi as serverApi

players = serverApi.GetPlayerList()
if not players:
    _result = {'error': 'no players in the managed test world'}
else:
    factory = serverApi.GetEngineCompFactory()
    component = factory.CreateBlock(serverApi.GetLevelId())
    palette = component.GetBlankBlockPalette()
    _result = json.dumps({
        'palette_type': type(palette).__name__,
        'serialized': palette.SerializeBlockPalette() if palette is not None else None,
    }, sort_keys=True)
