# -*- coding: utf-8 -*-
"""Fixed reference, floor-lever and wire-support views for the OB-10 report."""
from __future__ import unicode_literals

METADATA = ('test.blocks.concrete_neighbors', 'registry', '混凝土 · 拉杆邻接颜色',
            (18, 4, 18), 'minecraft:white_concrete')
PATCHES = tuple({'kind': kind, 'material': 'minecraft:' + color + '_concrete',
                 'center': (x, 1, z)}
                for kind, z in (('reference', 3), ('lever', 8), ('lever_and_wires', 13))
                for color, x in (('white', 4), ('light_gray', 12)))
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
    'focus': (8, 1, 8), 'cells': PATCHES,
    'modes': ('editor', 'full', 'missing'),
    'camera': {'editor': (35., 35., 1.5), 'world_offset': (-12., 14., -19.)},
    'default_opacity': .45, 'opaque_control': 1.,
    'known_remaining': 'Wire support cells may still brighten; they are a separate negative control.',
    'manual_acceptance': 'pending', 'redstone_simulation': False,
}


def populate(fixture):
    from .debug_blueprints import material
    lever = material('lever', {'lever_direction': 'up_north_south', 'open_bit': False})
    wire = material('redstone_wire', {'redstone_signal': 0})
    for row in PATCHES:
        x, y, z = row['center']
        support = material(row['material'])
        for dx in (-1, 0, 1):
            for dz in (-1, 0, 1):
                fixture.put((x + dx, y, z + dz), support)
        if row['kind'] != 'reference':
            fixture.put((x, y + 1, z), lever)
        if row['kind'] == 'lever_and_wires':
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                fixture.put((x + dx, y + 1, z + dz), wire)
    return fixture.finish()
