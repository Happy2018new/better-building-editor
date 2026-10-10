# -*- coding: utf-8 -*-
"""Supported native dripstone chains and explicit merged-tip snapshots."""
from __future__ import unicode_literals

METADATA = ('test.connections.dripstone', 'connections', '滴水石锥',
            (32, 24, 24), 'minecraft:pointed_dripstone')
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0],
    'chains': tuple({'length': length,
                     'standing': tuple((3 + index * 5, 1 + offset, 3) for offset in range(length)),
                     'hanging': tuple((3 + index * 5, 19 - offset, 11) for offset in range(length))}
                    for index, length in enumerate(range(1, 6))),
    'merged_tips': ((27, 3, 18), (27, 4, 18)),
    'vertical_chunk_cells': ((23, 16, 11), (23, 15, 11)),
    'camera': {'view': 'side', 'offset': (0., 0., 8.), 'cell_hull_height': 1.},
}


def populate(fixture):
    from .debug_blueprints import material
    fixture.floor()
    for row in VISUAL_CASE['chains']:
        length = row['length']
        thicknesses = (('tip',) if length == 1 else ('frustum', 'tip') if length == 2 else
                       ('base',) + ('middle',) * (length - 3) + ('frustum', 'tip'))
        for hanging, key in ((False, 'standing'), (True, 'hanging')):
            for pos, thickness in zip(row[key], thicknesses):
                fixture.put(pos, material('pointed_dripstone', {
                    'hanging': hanging, 'dripstone_thickness': thickness}))
        top = row['hanging'][0]
        fixture.put((top[0], top[1] + 1, top[2]), material('stone'))
    for hanging, pos in enumerate(VISUAL_CASE['merged_tips']):
        fixture.put(pos, material('pointed_dripstone', {
            'hanging': bool(hanging), 'dripstone_thickness': 'merge'}))
        fixture.put((pos[0], pos[1] + (1 if hanging else -1), pos[2]), material('stone'))
    return fixture.finish()
