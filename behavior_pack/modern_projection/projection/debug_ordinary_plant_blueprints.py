# -*- coding: utf-8 -*-
"""Small native-identity comparison for the three cross-plant fallbacks."""
from __future__ import unicode_literals

METADATA = ('test.blocks.ordinary_plant_visibility', 'registry', '树苗与珊瑚 · 四向可见性',
            (16, 5, 8), 'minecraft:acacia_sapling')
ROWS = ((3, 'acacia_sapling', {'age_bit': False}),
        (6, 'acacia_sapling', {'age_bit': True}),
        (9, 'brain_coral', {}), (12, 'bubble_coral', {}))
CORAL_METADATA = ('test.blocks.coral_plant_visibility', 'registry', '珊瑚植物 · 存活与失活',
                  (18, 5, 11), 'minecraft:fire_coral')
CORAL_NAMES = tuple(prefix + family + '_coral'
                    for prefix in ('', 'dead_')
                    for family in ('brain', 'bubble', 'fire', 'horn', 'tube'))


def populate(fixture):
    from .debug_blueprints import material
    support = material('stone')
    for x, name, states in ROWS:
        fixture.put((x, 1, 3), support)
        fixture.put((x, 2, 3), material(name, states))
    return fixture.finish()


def populate_corals(fixture):
    from .debug_blueprints import material
    support = material('stone')
    for index, name in enumerate(CORAL_NAMES):
        x, z = 2 + (index % 5) * 3, 3 + (index // 5) * 4
        fixture.put((x, 1, z), support)
        fixture.put((x, 2, z), material(name))
    return fixture.finish()
