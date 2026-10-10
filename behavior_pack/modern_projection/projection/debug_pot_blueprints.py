"""Public four-direction pottery fixture using native nondefault NBT only."""
from __future__ import unicode_literals

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


def populate(fixture):
    from .debug_blueprints import material, tag
    fixture.floor()
    for row in CASES:
        fixture.put(row['position'], material('decorated_pot', {'direction': row['direction']}),
                    entity='DecoratedPot', fields={'sherds': [tag(name, 8) for name in SHERDS]})
    return fixture.finish()
