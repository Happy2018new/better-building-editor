# -*- coding: utf-8 -*-
"""Read one managed-world palette through the editor's client API path."""
import json
import mod.client.extraClientApi as clientApi

low = (2, 66, 0)
high = (4, 67, 0)
block = clientApi.GetEngineCompFactory().CreateBlock(clientApi.GetLevelId())
palette = block.GetBlockPaletteBetweenPos(low, high, False)
if palette is None:
    _result = {'error': 'GetBlockPaletteBetweenPos returned None',
               'low': low, 'high': high}
else:
    serialized = palette.SerializeBlockPalette()
    _result = repr({
        'low': low,
        'high': high,
        'keys': sorted(serialized.keys()),
        'palette': serialized,
    })
