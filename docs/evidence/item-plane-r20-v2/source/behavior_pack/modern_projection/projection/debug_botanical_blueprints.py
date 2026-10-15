# -*- coding: utf-8 -*-
"""Unaccepted saved plant chains and tripwire snapshots for native comparison."""
from __future__ import unicode_literals

METADATA = ('test.connections.botanical', 'connections', 'Plant Chains and Tripwire',
            (64, 12, 64), 'minecraft:bamboo')


def _column(name, properties=None):
    return tuple(((0, y, 0), name, dict(properties or {})) for y in (2, 3, 4))


def _plant_cases():
    ground = (((0, 1, 0), 'stone', {}),)
    rows = [
        ('cactus_flower', _column('cactus') + (((0, 5, 0), 'cactus_flower', {}),),
         (((0, 1, 0), 'sand', {}),), ()),
        ('bamboo_leaves', (
            ((0, 2, 0), 'bamboo', {'bamboo_stalk_thickness': 'thin', 'bamboo_leaf_size': 'no_leaves'}),
            ((0, 3, 0), 'bamboo', {'bamboo_stalk_thickness': 'thick', 'bamboo_leaf_size': 'small_leaves'}),
            ((0, 4, 0), 'bamboo', {'bamboo_stalk_thickness': 'thick', 'bamboo_leaf_size': 'large_leaves'})),
         ground, ()),
        ('reeds_water_support', _column('reeds'),
         (((0, 1, 0), 'sand', {}), ((-1, 1, 0), 'water', {})), ()),
        ('kelp_wet_chain', _column('kelp'), ground, ((0, 2, 0), (0, 3, 0), (0, 4, 0))),
        ('weeping_vines_chain', _column('weeping_vines'), (((0, 5, 0), 'netherrack', {}),), ()),
        ('twisting_vines_chain', _column('twisting_vines'), ground, ()),
        ('cave_vines_plain', _column('cave_vines'), (((0, 5, 0), 'stone', {}),), ()),
        ('cave_vines_berries', (
            ((0, 4, 0), 'cave_vines', {}),
            ((0, 3, 0), 'cave_vines_body_with_berries', {}),
            ((0, 2, 0), 'cave_vines_head_with_berries', {})), (((0, 5, 0), 'stone', {}),), ()),
        ('vine_sides', _column('vine', {'vine_direction_bits': 15}),
         tuple(((x, y, z), 'stone', {}) for y in (2, 3, 4)
               for x, z in ((-1, 0), (1, 0), (0, -1), (0, 1))), ()),
        ('chorus_branch', (((0, 2, 0), 'chorus_plant', {}), ((0, 3, 0), 'chorus_plant', {}),
                           ((1, 3, 0), 'chorus_plant', {}), ((1, 4, 0), 'chorus_flower', {})),
         (((0, 1, 0), 'end_stone', {}),), ()),
        ('dripleaf_stem', _column('big_dripleaf') + (
            ((0, 5, 0), 'big_dripleaf', {'big_dripleaf_head': True}),), ground, ()),
    ]
    result = []
    for number, row in enumerate(rows):
        identity, blocks, supports, wet = row
        origin = (5 + number % 4 * 16, 0, 5 + number // 4 * 16)

        def translated(pos):
            return tuple(pos[i] + origin[i] for i in range(3))

        blocks = tuple((translated(pos), name, states) for pos, name, states in blocks)
        supports = tuple((translated(pos), name, states) for pos, name, states in supports)
        cells = tuple(pos for pos, name, states in blocks)
        result.append({'id': identity, 'family': 'plant_chain', 'blocks': blocks, 'supports': supports,
                       'water': tuple(translated(pos) for pos in wet), 'cells': cells,
                       'keep': cells[1], 'occupied': cells[0],
                       'camera': {'view': 'side', 'offset': (0., -.6, 8.)}})
    return result


def _tripwire_case(identity, length, z):
    left, right = 4, 5 + length
    blocks = (((left, 2, z), 'tripwire_hook', {'direction': 3, 'attached_bit': True}),
              ((right, 2, z), 'tripwire_hook', {'direction': 1, 'attached_bit': True})) + tuple(
                  ((x, 2, z), 'trip_wire', {'attached_bit': True}) for x in range(left + 1, right))
    supports = tuple(((x, 1, z), 'stone', {}) for x in range(left, right + 1)) + (
        ((left - 1, 2, z), 'stone', {}), ((right + 1, 2, z), 'stone', {}))
    cells = tuple(pos for pos, name, states in blocks)
    return {'id': identity, 'family': 'tripwire', 'blocks': blocks, 'supports': supports,
            'water': (), 'cells': cells, 'keep': (15 if length > 16 else left + 2, 2, z),
            'occupied': (16 if length > 16 else left + 3, 2, z),
            'camera': {'view': 'top', 'offset': (-3.5, 5., -5.)}}


CASES = tuple(_plant_cases()) + (_tripwire_case('tripwire_short', 5, 52),
                                _tripwire_case('tripwire_cross_chunk_long', 24, 60))
VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3],
               'cell_hull_height': 1., 'projection_height': 24, 'editor_camera': (35., 25., 4.),
               'cases': CASES, 'acceptance': {'editor': 'pending', 'full': 'pending', 'missing': 'pending'},
               'limits': 'Registry-resolved saved snapshots; supports and directions need native equality. No growth or survival deletion.'}


def populate(fixture):
    from .debug_blueprints import material
    from .cell import AIR
    fixture.floor()
    for row in CASES:
        wet = set(row['water'])
        for pos, name, states in row['supports'] + row['blocks']:
            fixture.put(pos, material(name, states), material('water') if pos in wet else AIR)
    return fixture.finish()


def source_document(identity, include_supports=True):
    from .debug_blueprints import build
    from .model import Document
    row = next(row for row in CASES if row['id'] == identity)
    source = build(METADATA[0])
    positions = set(row['cells'])
    if include_supports:
        positions.update(pos for pos, name, states in row['supports'])
    return Document(source.size, dict((pos, source.get(pos)) for pos in positions), biome=source.biome)
