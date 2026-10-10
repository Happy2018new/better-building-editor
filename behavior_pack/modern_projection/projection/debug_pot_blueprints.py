"""Public four-direction pottery fixture using native nondefault NBT only."""
from __future__ import unicode_literals
from .debug_sign_blueprints import WET_CASES

IDENTITY = 'test.entities.pottery'
METADATA = (IDENTITY, 'entities', 'Block Entities - Pottery Artwork',
            (24, 6, 10), 'minecraft:decorated_pot')
SHERDS = ('minecraft:angler_pottery_sherd', 'minecraft:archer_pottery_sherd',
          'minecraft:arms_up_pottery_sherd', 'minecraft:blade_pottery_sherd')
CASES = tuple({'id': 'direction_' + str(direction), 'direction': direction,
               'position': (3 + direction * 5, 1, 3),
               'support': (3 + direction * 5, 0, 3)} for direction in range(4))
VISUAL_CASE = {'schema': 1, 'fixture': IDENTITY, 'cases': CASES,
               'isolated_size': (3, 3, 3), 'focus': (1, 1, 1),
               'projection_height': 32,
               'camera': {'editor': (35., 10., 2.8),
                          'world_offset': (-2.5, -.3, -3.5)}}
WET_VISUAL_CASE = {'schema': 1, 'fixture': IDENTITY, 'cases': WET_CASES,
                   'camera_offset': (0., .4, 4.), 'projection_height': 24,
                   'scope': 'Wet decorated pot, independent dry control, adjacent water, and wet fence context'}


def populate(fixture):
    from .debug_blueprints import material, tag
    from .cell import AIR, actor_data, foreground, make_cell, rebase
    fixture.floor()
    for row in CASES:
        fixture.put(row['position'], material('decorated_pot', {'direction': row['direction']}),
                    entity='DecoratedPot', fields={'sherds': [tag(name, 8) for name in SHERDS]})
    base = fixture.document.get(CASES[0]['position'])
    water = material('water')
    for case in WET_CASES:
        value = rebase(base, tuple(case['actor'][i] - CASES[0]['position'][i] for i in range(3)))
        fixture.document.blocks[case['actor']] = make_cell(foreground(value), water, actor_data(value))
        if case['id'] == 'isolated':
            fixture.document.blocks[case['keep']] = rebase(
                base, tuple(case['keep'][i] - CASES[0]['position'][i] for i in range(3)))
        else:
            fixture.put(case['keep'], water if case['id'] == 'adjacent_water' else material('oak_fence'),
                        back=AIR if case['id'] == 'adjacent_water' else water)
        for pos in case['supports']:
            fixture.put(pos, material('stone' if pos[1] == 0 else 'glass'))
    return fixture.finish()
