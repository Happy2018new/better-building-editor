"""Export client-native six-face palettes; set sys._p0_shulker_face_positions.

The host passes the setup rows to this client script. Complete palettes stay in
sys._p0_shulker_face_palettes for rendering; JSON evidence uses material rows to
avoid losing tuple keys. Does not read server block entities or inventories.
"""
import json
import sys
import mod.client.extraClientApi as api
from modern_projection.projection.nbt_spatial import root_payload, scalar

component = api.GetEngineCompFactory().CreateBlock(api.GetLevelId())
rows = []
palettes = {}
for source in sys._p0_shulker_face_positions:
    pos = tuple(source['pos'])
    palette = component.GetBlockPaletteBetweenPos(pos, pos, False)
    assert palette is not None, ('Native palette unavailable', pos)
    data = palette.SerializeBlockPalette()
    assert data.get('actor'), ('Client replication or entity actor not ready', pos)
    payloads = [payload for entries in data['actor'].values() for payload in entries.values()]
    assert len(payloads) == 1, ('Expected one native shulker actor', pos)
    direction = scalar(root_payload(payloads[0]), 'facingDirection')
    assert type(direction) is int and 0 <= direction <= 5, ('Native facingDirection missing', pos, payloads)
    assert direction not in palettes, ('Native face placement did not produce six distinct directions', direction)
    palettes[direction] = data
    row = dict(source)
    row['observed_facing_direction'] = direction
    row['palette'] = dict((key, value) for key, value in data.items()
                          if key not in ('common', 'extra', 'states', 'extraStates'))
    for field in ('common', 'extra', 'states', 'extraStates'):
        row['palette'][field] = [{'material': key, 'value': value}
                                  for key, value in data.get(field, {}).items()]
    rows.append(row)
assert set(palettes) == set(range(6)), ('Incomplete native direction sample', sorted(palettes))
sys._p0_shulker_face_palettes = [palettes[direction] for direction in range(6)]
_result = json.dumps({'schema': 1, 'source': 'actual client palette after player placement',
                      'rows': rows})
