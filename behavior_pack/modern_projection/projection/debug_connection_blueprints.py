# -*- coding: utf-8 -*-
"""Fixed gate and six-face chorus scenes for independent native comparisons."""
from __future__ import unicode_literals
from . import block_registry as registry

METADATA = ('test.connections.static', 'connections', '栅栏门与紫颂连接',
            (64, 12, 64), 'minecraft:fence_gate')


def _gate_cases():
    names = tuple(sorted(name for name in registry.DEFAULT_AUX if name.endswith('_fence_gate'))) + (
        'minecraft:fence_gate',)
    rows = []
    for number, variant in enumerate((name, direction, opened) for name in names
                                     for direction in ('north', 'east') for opened in (False, True)):
        name, direction, opened = variant
        x, z = 4 + number % 8 * 8, 4 + number // 8 * 9
        axis = (1, 0, 0) if direction == 'north' else (0, 0, 1)
        gate, free = (x, 1, z), (x, 1, z + 4)
        walls = tuple(tuple(gate[i] + sign * axis[i] for i in range(3)) for sign in (-1, 1))
        fence = tuple(free[i] + axis[i] for i in range(3))
        identity = name.split(':')[1] + '_' + direction + ('_open' if opened else '_closed')
        camera = {'view': 'side', 'offset': (0., -.6, 7.) if direction == 'north' else (7., -.6, 0.)}
        rows.extend(({'id': identity + '_wall', 'family': 'gate', 'name': name,
                      'direction': direction, 'open': opened, 'in_wall': True,
                      'keep': gate, 'occupied': walls[1], 'cells': (gate,) + walls,
                      'camera': camera},
                     {'id': identity + '_fence', 'family': 'gate', 'name': name,
                      'direction': direction, 'open': opened, 'in_wall': False,
                      'keep': free, 'occupied': fence, 'cells': (free, fence),
                      'camera': camera}))
    return tuple(rows)


def _chorus_case(identity, center):
    x, y, z = center
    cells = (center, (x + 1, y, z), (x - 1, y, z), (x, y, z - 1),
             (x, y, z + 1), (x, y - 1, z), (x, y + 1, z))
    return {'id': identity, 'family': 'chorus', 'keep': center,
            'occupied': cells[1], 'cells': cells,
            'camera': {'view': 'side', 'offset': (0., -.7, 8.)}}


VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'cell_hull_height': 1.,
               'projection_height': 24, 'size': METADATA[3],
               'editor_camera': (35., 25., 4.),
               'cases': _gate_cases() + (_chorus_case('chorus_six_faces', (40, 5, 59)),
                                        _chorus_case('chorus_six_faces_cross_chunk', (15, 5, 59)))}


def populate(fixture):
    from .debug_blueprints import material
    fixture.floor()
    for row in VISUAL_CASE['cases']:
        if row['family'] == 'gate':
            fixture.put(row['keep'], material(row['name'], {
                'minecraft:cardinal_direction': row['direction'],
                'open_bit': row['open'], 'in_wall_bit': row['in_wall']}))
            for pos in row['cells'][1:]:
                fixture.put(pos, material('cobblestone_wall' if row['in_wall'] else 'oak_fence'))
        else:
            for pos in row['cells']:
                fixture.put(pos, material('chorus_flower' if pos[1] == row['keep'][1] + 1 else 'chorus_plant'))
            root = min(row['cells'], key=lambda pos: pos[1])
            fixture.put((root[0], root[1] - 1, root[2]), material('end_stone'))
    return fixture.finish(reconnect=True)
