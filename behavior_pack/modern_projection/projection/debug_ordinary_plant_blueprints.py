# -*- coding: utf-8 -*-
"""Small native-identity comparisons for centered plant visibility."""
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


PEONY_METADATA = ('test.blocks.peony_visibility', 'registry', '芍药 · 整株／下半／上半',
                  (16, 6, 8), 'minecraft:peony')
# Left to right: complete pair, isolated lower half, isolated upper half.
# Keep the orphan upper at the complete pair's upper height; the gap is intentional.
PEONY_CASES = (
    ('complete_pair', (3, 1, 3), (((3, 2, 3), False), ((3, 3, 3), True))),
    ('isolated_lower', (8, 1, 3), (((8, 2, 3), False),)),
    ('isolated_upper', (12, 1, 3), (((12, 3, 3), True),)),
)


def populate_peonies(fixture):
    from .debug_blueprints import material
    support = material('stone')
    for unused_case, support_pos, halves in PEONY_CASES:
        fixture.put(support_pos, support)
        for position, upper in halves:
            fixture.put(position, material('peony', {'upper_block_bit': upper}))
    return fixture.finish()


KELP_METADATA = ('test.blocks.kelp_visibility', 'registry', '海带 · 茎顶／孤立／跨区块',
                 (16, 18, 8), 'minecraft:kelp')
# Left to right: same-age column, isolated age25 head, same-age Y15/Y16 column.
KELP_CASES = (
    ('same_age_pair', (3, 1, 3), (((3, 2, 3), 0), ((3, 3, 3), 0))),
    ('isolated_head', (8, 1, 3), (((8, 2, 3), 25),)),
    ('cross_chunk_pair', (12, 14, 3), (((12, 15, 3), 0), ((12, 16, 3), 0))),
)


def populate_kelp(fixture):
    from .debug_blueprints import material
    support = material('stone')
    for unused_case, support_pos, chain in KELP_CASES:
        fixture.put(support_pos, support)
        for position, age in chain:
            fixture.put(position, material('kelp', {'kelp_age': age}))
    return fixture.finish()
