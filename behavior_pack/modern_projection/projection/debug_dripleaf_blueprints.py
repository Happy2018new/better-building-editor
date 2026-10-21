# -*- coding: utf-8 -*-
"""Separate captured dripleaf head/stem states from variable-length chains."""
from __future__ import unicode_literals

METADATA = ('test.blocks.dripleaf_states', 'registry', '大型垂滴叶 · 叶头／茎／倾斜',
            (26, 7, 60), 'minecraft:big_dripleaf')
DIRECTIONS = ('south', 'west', 'north', 'east')
TILTS = ('none', 'unstable', 'partial_tilt', 'full_tilt')


def _cases():
    result = []
    for column, direction in enumerate(DIRECTIONS):
        x = 3 + column * 6
        for head in (True, False):
            for row, tilt in enumerate(TILTS):
                z = 3 + (row + (0 if head else 4)) * 5
                result.append({'id': '%s_%s_%s' % ('head' if head else 'stem', direction, tilt),
                               'direction': direction, 'tilt': tilt, 'head': head,
                               'position': (x, 2, z), 'stem_length': None})
        for row, length in enumerate((0, 1, 3)):
            result.append({'id': 'chain_%s_%d' % (direction, length),
                           'direction': direction, 'tilt': 'none', 'head': True,
                           'position': (x, 2 + length, 45 + row * 5),
                           'stem_length': length})
    return tuple(result)


CASES = _cases()
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3], 'cases': CASES,
    'modes': ('editor', 'full', 'missing'),
    'editor_camera': (35., 25., 1.1),
    'layout': 'Four direction columns; four head tilt rows, four isolated stem rows, then chains of 0/1/3 stems.',
    'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
    'limits': 'Saved registry states only. No survival, growth, powered behavior or automatic tilt simulation. No dripleaf renderer fix is implied.',
}


def populate(fixture):
    from .debug_blueprints import material

    def dripleaf(direction, head, tilt):
        return material('big_dripleaf', {'big_dripleaf_head': head,
                                        'big_dripleaf_tilt': tilt,
                                        'minecraft:cardinal_direction': direction})

    support = material('stone')
    for row in CASES:
        x, y, z = row['position']
        length = row['stem_length']
        fixture.put((x, 1, z), support)
        if length is not None:
            for stem_y in range(2, y):
                fixture.put((x, stem_y, z), dripleaf(row['direction'], False, 'none'))
        fixture.put((x, y, z), dripleaf(row['direction'], row['head'], row['tilt']))
    return fixture.finish()
