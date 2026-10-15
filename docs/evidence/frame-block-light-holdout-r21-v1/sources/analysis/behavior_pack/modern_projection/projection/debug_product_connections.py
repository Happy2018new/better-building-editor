# -*- coding: utf-8 -*-
"""Small, supported product cases with independently declared transform states."""
from __future__ import unicode_literals

METADATA = ('test.connections.product', 'connections', '多格与混合连接验收',
            (56, 8, 56), 'minecraft:oak_stairs')
_SIDE = {'view': 'side', 'offset': (0., -.8, 7.)}
_SIDE_X = {'view': 'side', 'offset': (7., -.8, 0.)}
_TOP = {'view': 'top', 'offset': (-3.5, 5., -5.)}
_STAIR_DIRECTIONS = {
    'rotate_y90': (2, 3, 1, 0),
    'mirror_x': (1, 0, 2, 3),
    'mirror_z': (0, 1, 3, 2),
}


def _transform_point(pos, operation):
    x, y, z = pos
    if operation == 'rotate_y90':
        return -z, y, x
    if operation == 'mirror_x':
        return -x, y, z
    if operation == 'mirror_z':
        return x, y, -z
    return pos


def _stairs(identity, kind, operation, upside_down=False):
    neighbor = (1, 0, 0) if kind == 'outer' else (-1, 0, 0)
    initial = (((0, 0, 0), 'oak_stairs', 0), (neighbor, 'brick_stairs', 3))
    directions = _STAIR_DIRECTIONS.get(operation, (0, 1, 2, 3))
    blocks = tuple((_transform_point(pos, operation), name, {
        'weirdo_direction': directions[direction], 'upside_down_bit': upside_down})
                   for pos, name, direction in initial)
    source = tuple((pos, name, {'weirdo_direction': direction, 'upside_down_bit': upside_down})
                   for pos, name, direction in initial)
    camera = _SIDE_X if blocks[1][0][2] != blocks[0][0][2] else _SIDE
    return {'id': identity, 'family': 'stairs', 'blocks': blocks, 'source_blocks': source,
            'operation': operation, 'keep': blocks[0][0], 'occupied': blocks[1][0], 'camera': camera}


def _line(identity, family, names, camera=_SIDE):
    blocks = tuple(((index - 1, 0, 0), name, {}) for index, name in enumerate(names))
    return {'id': identity, 'family': family, 'blocks': blocks,
            'keep': (0, 0, 0), 'occupied': (1, 0, 0), 'camera': camera}


def _gate(identity, opened):
    row = _line(identity, 'gate', ('oak_fence', 'bamboo_fence_gate', 'spruce_fence'))
    row['blocks'] = (row['blocks'][0], ((0, 0, 0), 'bamboo_fence_gate', {
        'minecraft:cardinal_direction': 'north', 'open_bit': opened, 'in_wall_bit': False}),
                     row['blocks'][2])
    return row


def _wall(identity, upper_name, upper_states):
    blocks = []
    for x, name in ((-1, 'cobblestone_wall'), (0, 'brick_wall'), (1, 'mossy_cobblestone_wall')):
        blocks.append(((x, 0, 0), name, {
            'wall_connection_type_east': 'none' if x == 1 else 'tall' if x == 0 else 'short',
            'wall_connection_type_west': 'none' if x == -1 else 'tall' if x == 0 else 'short',
            'wall_connection_type_north': 'none', 'wall_connection_type_south': 'none',
            'wall_post_bit': x != 0}))
    blocks.append(((0, 1, 0), upper_name, upper_states))
    return {'id': identity, 'family': 'wall', 'blocks': tuple(blocks),
            'keep': (0, 0, 0), 'occupied': (1, 0, 0), 'camera': _SIDE}


def _rail(identity, name, ascending):
    if ascending:
        blocks = (((-1, 0, 0), name, {'rail_direction': 1}),
                  ((0, 0, 0), name, {'rail_direction': 2}),
                  ((1, 1, 0), name, {'rail_direction': 1}))
        occupied = (1, 1, 0)
    else:
        blocks = (((0, 0, 0), name, {'rail_direction': 6}),
                  ((1, 0, 0), name, {'rail_direction': 1}),
                  ((0, 0, 1), name, {'rail_direction': 0}))
        occupied = (1, 0, 0)
    return {'id': identity, 'family': 'rail', 'blocks': blocks,
            'keep': (0, 0, 0), 'occupied': occupied, 'camera': _TOP}


def _vertical(identity, name, lower, upper):
    return {'id': identity, 'family': 'fixed_group',
            'blocks': (((0, 0, 0), name, lower), ((0, 1, 0), name, upper)),
            'keep': (0, 0, 0), 'occupied': (0, 1, 0), 'camera': _SIDE,
            'group_closure': ((0, 0, 0), (0, 1, 0))}


def _cases():
    raw = [_stairs('stairs_outer_turn90', 'outer', 'rotate_y90'),
           _stairs('stairs_outer_mirror_x', 'outer', 'mirror_x'),
           _stairs('stairs_inner_mirror_z', 'inner', 'mirror_z'),
           _stairs('stairs_inner_inverted_turn90', 'inner', 'rotate_y90', True),
           _gate('fence_mixed_closed_gate', False), _gate('fence_mixed_open_gate', True),
           _line('pane_mixed_clear_red', 'pane', ('glass_pane', 'red_stained_glass_pane', 'glass_pane')),
           _line('pane_mixed_hardened', 'pane', ('hard_glass_pane', 'hard_blue_stained_glass_pane', 'hard_glass_pane')),
           _line('bars_mixed_copper_iron', 'bars', ('copper_bars', 'iron_bars', 'waxed_exposed_copper_bars')),
           _wall('wall_mixed_bottom_slab', 'oak_slab', {'minecraft:vertical_half': 'bottom'}),
           _wall('wall_mixed_normal_stair', 'oak_stairs', {'weirdo_direction': 0, 'upside_down_bit': False}),
           _rail('rail_supported_curve', 'rail', False)]
    raw.extend(_rail(name + '_supported_slope', name, True)
               for name in ('rail', 'golden_rail', 'detector_rail', 'activator_rail'))
    door = {'minecraft:cardinal_direction': 'east', 'door_hinge_bit': True, 'open_bit': True}
    raw.extend((_vertical('door_open_east_hinge', 'wooden_door', dict(door, upper_block_bit=False),
                          dict(door, upper_block_bit=True)),
                _vertical('fern_two_halves', 'large_fern', {'upper_block_bit': False}, {'upper_block_bit': True}),
                _vertical('pitcher_mature_two_halves', 'pitcher_crop',
                          {'growth': 3, 'upper_block_bit': False}, {'growth': 3, 'upper_block_bit': True})))
    rows = []
    for number, source in enumerate(raw):
        delta = (5 + number % 6 * 8, 2, 5 + number // 6 * 8)
        point = lambda pos: tuple(pos[i] + delta[i] for i in range(3))
        row = dict(source)
        row['blocks'] = tuple((point(pos), name, properties) for pos, name, properties in source['blocks'])
        row['cells'] = tuple(pos for pos, name, properties in row['blocks'])
        row['keep'], row['occupied'] = point(source['keep']), point(source['occupied'])
        # One support per lowest body column, avoiding support/body overlap.
        columns = {}
        for pos in row['cells']:
            column = pos[0], pos[2]
            columns[column] = min(pos[1], columns.get(column, pos[1]))
        row['supports'] = tuple(((x, height - 1, z), 'dirt' if row['family'] == 'fixed_group' else 'stone', {})
                                for (x, z), height in sorted(columns.items()))
        row['group_closure'] = tuple(point(pos) for pos in source.get('group_closure', (source['keep'],)))
        row['source_blocks'] = tuple((point(pos), name, properties)
                                     for pos, name, properties in source.get('source_blocks', ()))
        row['transform_origin'] = delta
        row['acceptance'] = {'editor_presence': 'pending', 'editor_shape': 'pending',
                             'full': 'pending', 'missing': 'pending'}
        rows.append(row)
    return tuple(rows)


VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
               'cell_hull_height': 1., 'projection_height': 2,
               'editor_camera': (35., 25., 3.), 'cases': _cases(),
               'limits': 'Dry supported snapshots; no NBT, survival or fluid simulation. '
                         'Chest real occupancy and colored beds use separate actor-aware holdouts.'}


def populate(fixture):
    from .debug_blueprints import material
    for row in VISUAL_CASE['cases']:
        for pos, name, properties in row['supports'] + row['blocks']:
            fixture.put(pos, material(name, properties))
    return fixture.finish()


def source_document(identity, include_supports=True):
    from .debug_blueprints import build
    from .model import Document
    row = next(row for row in VISUAL_CASE['cases'] if row['id'] == identity)
    source = build(METADATA[0])
    positions = set(row['cells'])
    if include_supports:
        positions.update(pos for pos, name, properties in row['supports'])
    return Document(source.size, dict((pos, source.get(pos)) for pos in positions), biome=source.biome)
