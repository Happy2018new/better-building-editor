# -*- coding: utf-8 -*-
"""Public source snapshots and edit actions for native neighbor comparisons."""
from __future__ import unicode_literals

METADATA = ('test.connections.actions', 'connections', 'Connection Edit Actions',
            (64, 12, 64), 'minecraft:rail')
RAIL_NAMES = ('rail', 'golden_rail', 'detector_rail', 'activator_rail')


def _rail_cases():
    rows = []
    layouts = (
        ('corner', ((0, 0, -1), (1, 0, 0), None, (0, 0, 1), (-1, 0, 0))),
        ('slope', ((1, 1, 0), (2, 1, 0), None, (1, 1, 0))),
        ('junction_ns_first', ((0, 0, -1), (0, 0, 1), (1, 0, 0), (-1, 0, 0), None)),
        ('junction_ew_first', ((1, 0, 0), (-1, 0, 0), (0, 0, -1), (0, 0, 1), None)),
    )
    for name in RAIL_NAMES:
        for layout, sequence in layouts:
            blocks, actions = (((0, 2, 0), name, {}),), []
            previous = None
            for index, offset in enumerate(sequence):
                if offset is None:
                    actions.append(('erase_' + str(index), ((previous, 'air', {}),)))
                    continue
                previous = (offset[0], offset[1] + 2, offset[2])
                actions.append(('place_' + str(index), ((previous, name, {}),)))
            positions = {(0, 2, 0)} | {pos for identity, writes in actions for pos, block, properties in writes}
            supports = tuple((tuple(pos[i] - (0, 1, 0)[i] for i in range(3)), 'stone', {})
                             for pos in sorted(positions))
            rows.append({'id': name + '_' + layout, 'family': 'rail', 'blocks': blocks,
                         'supports': supports, 'actions': tuple(actions), 'focus': (0, 2, 0)})
    return rows


def _other_cases():
    rows = []
    for inverted in (False, True):
        for corner, offset in (('outer', (1, 0, 0)), ('inner', (-1, 0, 0))):
            center, neighbor = (0, 2, 0), (offset[0], 2, offset[2])
            properties = {'weirdo_direction': 0, 'upside_down_bit': inverted}
            turning = {'weirdo_direction': 3, 'upside_down_bit': inverted}
            rows.append({'id': 'stair_' + corner + ('_inverted' if inverted else '_standing'),
                         'family': 'stairs', 'blocks': ((center, 'oak_stairs', properties),),
                         'supports': tuple(((x, 1, 0), 'stone', {}) for x in (-1, 0, 1)),
                         'actions': (('form_corner', ((neighbor, 'birch_stairs', turning),)),
                                     ('erase_corner', ((neighbor, 'air', {}),))), 'focus': center})
    for name, partner in (('cobblestone_wall', 'glass_pane'), ('oak_fence', 'birch_fence'),
                          ('glass_pane', 'red_stained_glass_pane'), ('iron_bars', 'copper_bars')):
        center, neighbor = (0, 2, 0), (1, 2, 0)
        rows.append({'id': name + '_mixed', 'family': 'connections',
                     'blocks': ((center, name, {}),),
                     'supports': tuple(((x, 1, 0), 'stone', {}) for x in (0, 1)),
                     'actions': (('connect', ((neighbor, partner, {}),)),
                                 ('erase', ((neighbor, 'air', {}),))), 'focus': center})
    return rows


def _translated(row, number):
    origin = (4 + number % 8 * 8, 0, 4 + number // 8 * 10)

    def pos(value):
        return tuple(value[i] + origin[i] for i in range(3))

    result = dict(row)
    for field in ('blocks', 'supports'):
        result[field] = tuple((pos(point), name, properties) for point, name, properties in row[field])
    result['actions'] = tuple((identity, tuple((pos(point), name, properties)
                                              for point, name, properties in writes))
                              for identity, writes in row['actions'])
    result['focus'] = pos(row['focus'])
    return result


CASES = tuple(_translated(row, number) for number, row in enumerate(_rail_cases() + _other_cases()))
ACTION_MATRIX = {'schema': 1, 'fixture': METADATA[0], 'size': METADATA[3], 'cases': CASES,
                 'acceptance': {'state_actions': 'pending', 'editor': 'pending',
                                'full': 'pending', 'missing': 'pending'},
                 'limits': 'Declared snapshot edits; no signal propagation, support deletion or survival simulation.'}


def populate(fixture):
    from .debug_blueprints import material
    fixture.floor()
    for row in CASES:
        for pos, name, properties in row['supports'] + row['blocks']:
            fixture.put(pos, material(name, properties))
    return fixture.finish()


def source_document(identity):
    from .debug_blueprints import build
    from .model import Document
    row = next(row for row in CASES if row['id'] == identity)
    source = build(METADATA[0])
    positions = set(pos for pos, name, properties in row['supports'] + row['blocks'])
    return Document(source.size, dict((pos, source.get(pos)) for pos in positions), biome=source.biome)
