# -*- coding: utf-8 -*-
"""Native barrier cells for three-view marker and partial-occupancy checks."""
from __future__ import unicode_literals

METADATA = ('test.blocks.barrier_visibility', 'registry', '屏障 · 三轴可视标记',
            (16, 8, 16), 'minecraft:barrier')
ISOLATED = (3, 3, 3)
ADJACENT = ((7, 3, 3), (8, 3, 3))
PANEL = tuple((x, y, 9) for x in range(3, 6) for y in range(2, 5))
FLOATING = (11, 5, 9)
BARRIERS = (ISOLATED,) + ADJACENT + PANEL + (FLOATING,)
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
    'focus': (7, 3, 6), 'cells': BARRIERS, 'isolated': ISOLATED,
    'adjacent': ADJACENT, 'panel': PANEL, 'floating': FLOATING,
    'stone_control': (11, 3, 3), 'modes': ('editor', 'full', 'missing'),
    'camera': {'editor': (35., 25., 2.), 'world_offset': (-8., 5., -12.)},
    'views': ('north', 'south', 'east', 'west', 'above', 'below', 'diagonal'),
    'partial_occupancy': (ISOLATED, ADJACENT[0], PANEL[4]),
    'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
    'marker_is_native_block_appearance': False,
    'native_world_block_identity': 'minecraft:barrier',
}


def populate(fixture):
    from .debug_blueprints import material
    barrier, stone = material('barrier'), material('stone')
    for pos in BARRIERS:
        fixture.put(pos, barrier)
    for x, z in ((3, 3), (7, 3), (8, 3), (11, 3), (11, 9)):
        fixture.put((x, 1, z), material('light_gray_concrete'))
    fixture.put(VISUAL_CASE['stone_control'], stone)
    return fixture.finish()


def build():
    from .debug_blueprints import Fixture
    return populate(Fixture(METADATA))
