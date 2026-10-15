# -*- coding: utf-8 -*-
"""Public slab fixtures and the click coordinates used by interaction checks."""
from __future__ import unicode_literals

METADATA = ('test.groups.slabs', 'groups', '半砖放置、合并与破坏',
            (24, 8, 20), 'minecraft:oak_slab')
CASES = (
    {'id': 'oak_bottom', 'pos': (3, 2, 4), 'name': 'oak_slab', 'half': 'bottom'},
    {'id': 'oak_top', 'pos': (8, 2, 4), 'name': 'oak_slab', 'half': 'top'},
    {'id': 'oak_double', 'pos': (13, 2, 4), 'name': 'oak_double_slab', 'half': 'bottom'},
    {'id': 'copper_bottom', 'pos': (3, 2, 9), 'name': 'cut_copper_slab', 'half': 'bottom'},
    {'id': 'copper_top', 'pos': (8, 2, 9), 'name': 'cut_copper_slab', 'half': 'top'},
    {'id': 'copper_double', 'pos': (13, 2, 9), 'name': 'double_cut_copper_slab', 'half': 'bottom'},
    {'id': 'wet_bottom', 'pos': (3, 2, 14), 'name': 'oak_slab', 'half': 'bottom', 'water': True},
    {'id': 'wet_top', 'pos': (8, 2, 14), 'name': 'oak_slab', 'half': 'top', 'water': True},
)
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3], 'cases': CASES,
    'camera': {'editor': (35., 25., 3.), 'world_offset': (-3.5, 2., -5.)},
    'projection_height': 24,
    'interaction': {
        'side_lower': {'normal': (1, 0, 0), 'local_hit': (1., .25, .5)},
        'side_upper': {'normal': (1, 0, 0), 'local_hit': (1., .75, .5)},
        'merge_bottom': {'normal': (0, 1, 0), 'local_hit': (.5, .5, .5)},
        'merge_top': {'normal': (0, -1, 0), 'local_hit': (.5, .5, .5)},
    },
    'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending',
                   'native_placement': 'pending'},
}


def populate(fixture):
    from .debug_blueprints import material
    from .cell import AIR
    fixture.floor()
    for case in CASES:
        pos = case['pos']
        fixture.put((pos[0], pos[1]-1, pos[2]), material('stone'))
        fixture.put(pos, material(case['name'], {'minecraft:vertical_half': case['half']}),
                    back=material('water') if case.get('water') else AIR)
    return fixture.finish()
