"""Export client-native six-face palettes; set sys._p0_shulker_face_positions.

The host passes the setup rows to this client script. Complete palettes stay in
sys._p0_shulker_face_palettes for rendering; JSON evidence uses material rows to
avoid losing tuple keys. Does not read server block entities or inventories.
"""
import json
import sys
import mod.client.extraClientApi as api

component = api.GetEngineCompFactory().CreateBlock(api.GetLevelId())
rows = []
palettes = []
for source in sys._p0_shulker_face_positions:
    pos = tuple(source['pos'])
    palette = component.GetBlockPaletteBetweenPos(pos, pos, False)
    assert palette is not None, ('Native palette unavailable', pos)
    data = palette.SerializeBlockPalette()
    assert data.get('actor'), ('Client replication or entity actor not ready', pos)
    palettes.append(data)
    row = dict(source)
    row['palette'] = dict((key, value) for key, value in data.items()
                          if key not in ('common', 'extra', 'states', 'extraStates'))
    for field in ('common', 'extra', 'states', 'extraStates'):
        row['palette'][field] = [{'material': key, 'value': value}
                                  for key, value in data.get(field, {}).items()]
    rows.append(row)
sys._p0_shulker_face_palettes = palettes
_result = json.dumps({'schema': 1, 'source': 'actual client palette after player placement',
                      'rows': rows})
