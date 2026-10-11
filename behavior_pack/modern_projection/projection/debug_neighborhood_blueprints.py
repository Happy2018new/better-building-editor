# -*- coding: utf-8 -*-
"""Small supported native neighborhoods with fixed visual comparison cells."""
from __future__ import unicode_literals

METADATA = ('test.connections.extended', 'connections', '脚手架、地毯、红石与藤链',
            (40, 12, 40), 'minecraft:scaffolding')
_SCAFFOLD = {'stability': 0, 'stability_check': False}
_MOSS_SIDE = {'pale_moss_carpet_side_east': 'short'}

_CASES = (
    {'id': 'scaffolding_column', 'family': 'scaffolding',
     'blocks': tuple(((4, y, 4), 'scaffolding', _SCAFFOLD) for y in (1, 2, 3)),
     'supports': (((4, 0, 4), 'stone', {}),),
     'keep': (4, 2, 4), 'occupied': (4, 3, 4),
     'camera': {'view': 'side', 'offset': (0., -.6, 7.)}},
    {'id': 'scaffolding_parallel_columns', 'family': 'scaffolding',
     'blocks': tuple(((x, y, 4), 'scaffolding', _SCAFFOLD) for x in (18, 19) for y in (1, 2)),
     'supports': tuple(((x, 0, 4), 'stone', {}) for x in (18, 19)),
     'keep': (18, 2, 4), 'occupied': (19, 2, 4),
     'camera': {'view': 'side', 'offset': (0., -.6, 7.)}},
    {'id': 'pale_moss_carpet_flat_pair', 'family': 'pale_moss_carpet',
     'blocks': tuple(((x, 1, 14), 'pale_moss_carpet', {}) for x in (4, 5)),
     'supports': tuple(((x, 0, 14), 'stone', {}) for x in (4, 5)),
     'keep': (4, 1, 14), 'occupied': (5, 1, 14),
     'camera': {'view': 'top', 'offset': (-3.5, 5., -5.)}},
    {'id': 'pale_moss_carpet_wall_pair', 'family': 'pale_moss_carpet',
     'blocks': tuple(((18, 1, z), 'pale_moss_carpet', _MOSS_SIDE) for z in (14, 15)),
     'supports': tuple(((18, 0, z), 'stone', {}) for z in (14, 15)) +
                 tuple(((19, 1, z), 'stone', {}) for z in (14, 15)),
     'keep': (18, 1, 14), 'occupied': (18, 1, 15),
     'camera': {'view': 'top', 'offset': (-3.5, 5., -5.)}},
    {'id': 'redstone_unpowered_line', 'family': 'redstone',
     'blocks': tuple(((x, 1, 24), 'redstone_wire', {'redstone_signal': 0}) for x in (4, 5, 6)),
     'supports': tuple(((x, 0, 24), 'stone', {}) for x in (4, 5, 6)),
     'keep': (5, 1, 24), 'occupied': (6, 1, 24),
     'camera': {'view': 'top', 'offset': (-3.5, 5., -5.)}},
    {'id': 'redstone_unpowered_corner', 'family': 'redstone',
     'blocks': tuple((pos, 'redstone_wire', {'redstone_signal': 0})
                     for pos in ((18, 1, 24), (19, 1, 24), (18, 1, 25))),
     'supports': tuple((pos, 'stone', {}) for pos in ((18, 0, 24), (19, 0, 24), (18, 0, 25))),
     'keep': (18, 1, 24), 'occupied': (19, 1, 24),
     'camera': {'view': 'top', 'offset': (-3.5, 5., -5.)}},
    {'id': 'weeping_vines_chain', 'family': 'vine_chain',
     'blocks': tuple(((4, y, 34), 'weeping_vines', {'weeping_vines_age': 0}) for y in (3, 2, 1)),
     'supports': (((4, 4, 34), 'netherrack', {}),),
     'keep': (4, 2, 34), 'occupied': (4, 1, 34),
     'camera': {'view': 'side', 'offset': (0., 0., 8.)}},
    {'id': 'twisting_vines_chain', 'family': 'vine_chain',
     'blocks': tuple(((18, y, 34), 'twisting_vines', {'twisting_vines_age': 0}) for y in (1, 2, 3)),
     'supports': (((18, 0, 34), 'warped_nylium', {}),),
     'keep': (18, 2, 34), 'occupied': (18, 3, 34),
     'camera': {'view': 'side', 'offset': (0., 0., 8.)}},
)
for _case in _CASES:
    _case['cells'] = tuple(pos for pos, name, properties in _case['blocks'])

VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
               'cell_hull_height': 1., 'projection_height': 24,
               'editor_camera': (35., 25., 4.), 'cases': _CASES,
               'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
               'limits': 'Fixed registry-resolved snapshots; no growth, power simulation or state replacement.'}


def populate(fixture):
    from .debug_blueprints import material
    fixture.floor()
    for row in _CASES:
        for pos, name, properties in row['supports'] + row['blocks']:
            fixture.put(pos, material(name, properties))
    return fixture.finish()


def source_document(identity, include_supports=True):
    from .debug_blueprints import build
    from .model import Document
    row = next(row for row in _CASES if row['id'] == identity)
    fixture = build(METADATA[0])
    positions = set(row['cells'])
    if include_supports:
        positions.update(pos for pos, name, properties in row['supports'])
    return Document(fixture.size, dict((pos, fixture.get(pos)) for pos in positions), biome=fixture.biome)
