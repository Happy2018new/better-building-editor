# -*- coding: utf-8 -*-
"""Small static signal comparison for the reported pressure-plate shape issue."""
from __future__ import unicode_literals

METADATA = ('test.blocks.pressure_signals', 'registry', '压力板 · 信号 0／1／15',
            (16, 5, 20), 'minecraft:stone_pressure_plate')
MATERIALS = ('stone_pressure_plate', 'wooden_pressure_plate',
             'light_weighted_pressure_plate', 'heavy_weighted_pressure_plate')
SIGNALS = (0, 1, 15)
ROWS = tuple({'material': 'minecraft:' + name, 'signal': signal,
              'position': (3 + column * 4, 2, 3 + row * 4)}
             for row, name in enumerate(MATERIALS)
             for column, signal in enumerate(SIGNALS))
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
    'focus': (7, 2, 9), 'cells': ROWS, 'modes': ('editor', 'full', 'missing'),
    'camera': {'editor': (35., 25., 2.), 'world_offset': (-8., 6., -12.)},
    'expected': 'Signal 0 is raised; signals 1 and 15 share the pressed shape.',
    'redstone_simulation': False, 'native_absolute_height_qualified': False,
    'manual_acceptance': 'pending',
}


def populate(fixture):
    from .debug_blueprints import material
    support = material('quartz_block')
    for row in ROWS:
        x, y, z = row['position']
        fixture.put((x, y - 1, z), support)
        fixture.put((x, y, z), material(row['material'], {'redstone_signal': row['signal']}))
    return fixture.finish()


def build():
    from .debug_blueprints import Fixture
    return populate(Fixture(METADATA))
