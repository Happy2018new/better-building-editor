"""Public cauldron snapshots for shared editor and projection acceptance."""
from __future__ import unicode_literals

from .cell import actor_data, make_cell
from .model import Document

METADATA = ('test.entities.cauldrons', 'entities', '\u70bc\u836f\u9505\u6db2\u9762\u4e0e\u989c\u8272',
            (40, 8, 32), 'minecraft:cauldron')
ISOLATED_SIZE = (8, 8, 8)
FOCUS = (3, 3, 3)


def _rows():
    rows = []
    for liquid in ('water', 'lava', 'powder_snow'):
        for fill in range(1, 7):
            rows.append({'id': liquid + str(fill), 'liquid': liquid, 'fill': fill,
                         'potion': -1, 'form': -1, 'color': None})
    for color, value in (('red', 0xff0000), ('blue', 0x0000ff), ('mixed', 0x325060)):
        rows.append({'id': 'custom_' + color, 'liquid': 'water', 'fill': 6,
                     'potion': -1, 'form': -1, 'color': value})
    for potion in (5, 12, 21, 43):
        for form in (0, 1, 2):
            rows.append({'id': 'potion_%d_%d' % (potion, form), 'liquid': 'water', 'fill': 6,
                         'potion': potion, 'form': form, 'color': None})
    return tuple(dict(row, anchor=(4 + index % 7 * 5, 2, 4 + index // 7 * 5))
                 for index, row in enumerate(rows))


CASES = _rows()
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': ISOLATED_SIZE, 'focus': FOCUS,
    'cases': CASES, 'controls': ('filled', 'empty'),
    'modes': ('editor', 'projection_full', 'projection_missing'),
    'camera': {'editor': (35., 45., 3.), 'world_offset': (2., 5., -3.)},
    'snapshot_only': True,
    'acceptance': {'source_actor_preserved': True, 'top_inside_shell': True,
                   'six_fill_levels': True, 'unknown_appearances_remain_native': True},
}


def populate(fixture):
    from .debug_blueprints import material, tag
    for row in CASES:
        position = row['anchor']
        fixture.put((position[0], position[1]-1, position[2]), material('stone'))
        fields = {'PotionId': tag(row['potion'], 2), 'PotionType': tag(row['form'], 2)}
        if row['color'] is not None:
            fields['CustomColor'] = tag(row['color'], 3)
        fixture.put(position, material('cauldron', {'cauldron_liquid': row['liquid'],
                                                   'fill_level': row['fill']}),
                    entity='Cauldron', fields=fields)
    return fixture.finish()


def source_document(identity, control='filled'):
    """Extract exact public gallery cells, retaining the complete source actor."""
    from .debug_blueprints import build, material
    row = next((item for item in CASES if item['id'] == identity), None)
    if row is None or control not in VISUAL_CASE['controls']:
        raise ValueError('Unknown cauldron case/control: ' + str((identity, control)))
    source = build(METADATA[0])
    result = Document(ISOLATED_SIZE, name=source.name, biome=source.biome)
    position = row['anchor']
    cell = source.get(position)
    if control == 'empty':
        cell = make_cell(material('cauldron', {'cauldron_liquid': 'water', 'fill_level': 0}),
                         nbt=actor_data(cell))
    result.set_cell(FOCUS, cell)
    result.set_cell((FOCUS[0], FOCUS[1]-1, FOCUS[2]),
                    source.get((position[0], position[1]-1, position[2])))
    return result
