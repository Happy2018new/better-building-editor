"""Retain actual client palettes and pair them with owned native fixture NBT."""
import json
import sys
import mod.client.extraClientApi as api

component = api.GetEngineCompFactory().CreateBlock(api.GetLevelId())
rows, palettes, pending = [], [], []
for original in sys._p0_entity_appearance_rows:
    cells = [tuple(pos) for pos in original['cells']]
    lo = tuple(min(pos[axis] for pos in cells) for axis in range(3))
    hi = tuple(max(pos[axis] for pos in cells) for axis in range(3))
    palette = component.GetBlockPaletteBetweenPos(lo, hi, False)
    if palette is None:
        pending.append((original['case'], 'palette unavailable'))
        continue
    data = palette.SerializeBlockPalette()
    expected = original.get('expected_block',
                            'minecraft:standing_banner' if original['name'] == 'minecraft:banner' else original['name'])
    if not any(value[0] == expected for value in data.get('common', {})):
        pending.append((original['case'], 'block not replicated'))
        continue
    palettes.append(data)
    row = dict(original, palette_origin=lo)
    row['palette'] = {key: value for key, value in data.items()
                      if key not in ('common', 'extra', 'states', 'extraStates')}
    for field in ('common', 'extra', 'states', 'extraStates'):
        row['palette'][field] = [{'material': key, 'value': value}
                                for key, value in data.get(field, {}).items()]
    rows.append(row)
if not pending:
    sys._p0_entity_appearance_palettes = palettes
    sys._p0_entity_appearance_entities = rows
_result = json.dumps({'schema': 1, 'ready': not pending, 'pending': pending,
                     'source': 'actual client palette after native player placement', 'rows': rows})
