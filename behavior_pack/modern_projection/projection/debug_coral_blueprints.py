# -*- coding: utf-8 -*-
"""Three bounded coral galleries; native source identity and layers stay intact."""
from __future__ import unicode_literals

SCHEMA_VERSION = 1
FAMILIES = ('brain', 'bubble', 'fire', 'horn', 'tube')
METADATA = (
    ('test.blocks.coral_blocks', 'registry', '珊瑚 ① · 十种原生珊瑚块',
     (27, 5, 12), 'minecraft:brain_coral_block'),
    ('test.blocks.coral_fans', 'registry', '珊瑚 ② · 六种扇状态与支撑对照',
     (32, 5, 18), 'minecraft:dead_brain_coral_fan'),
    ('test.layers.coral_plants', 'registry', '珊瑚 ③ · 十种植物与两种水层序',
     (27, 5, 33), 'minecraft:fire_coral'),
)
FAN_STATES = (
    ('floor0', 'dead_brain_coral_fan', 'coral_fan_direction', 0, (0, 1, 0)),
    ('floor1', 'dead_brain_coral_fan', 'coral_fan_direction', 1, (0, 1, 0)),
    ('wall0', 'dead_brain_coral_wall_fan', 'coral_direction', 0, (-1, 0, 0)),
    ('wall1', 'dead_brain_coral_wall_fan', 'coral_direction', 1, (1, 0, 0)),
    ('wall2', 'dead_brain_coral_wall_fan', 'coral_direction', 2, (0, 0, -1)),
    ('wall3', 'dead_brain_coral_wall_fan', 'coral_direction', 3, (0, 0, 1)),
)


def _block_rows():
    return tuple({'id': prefix + family, 'name': prefix + family + '_coral_block',
                  'position': (3 + column * 5, 2, 3 + group * 5)}
                 for group, prefix in enumerate(('', 'dead_'))
                 for column, family in enumerate(FAMILIES))


def _fan_rows():
    rows = []
    for column, (identity, name, state, value, outward) in enumerate(FAN_STATES):
        for group, control in enumerate(('air', 'stone', 'fan')):
            target = (3 + column * 5, 2, 3 + group * 5)
            support = tuple(target[i] - outward[i] for i in range(3))
            rows.append({'id': identity + '_' + control, 'case': identity, 'name': name,
                         'states': {state: value}, 'control': control,
                         'position': target, 'support': support})
    return tuple(rows)


def _plant_rows():
    rows = []
    for group, prefix in enumerate(('', 'dead_')):
        for order, control in enumerate(('dry', 'plant_water', 'water_plant')):
            for column, family in enumerate(FAMILIES):
                rows.append({'id': prefix + family + '_' + control,
                             'name': prefix + family + '_coral', 'control': control,
                             'position': (3 + column * 5, 2, 3 + (group * 3 + order) * 5)})
    return tuple(rows)


CASES = {METADATA[0][0]: _block_rows(), METADATA[1][0]: _fan_rows(),
         METADATA[2][0]: _plant_rows()}
VISUAL_CASES = dict((row[0], {'schema': SCHEMA_VERSION, 'fixture': row[0],
                    'cases': CASES[row[0]], 'modes': ('editor', 'projection_full', 'projection_missing'),
                    'acceptance': 'pending_manual_review', 'world_writes_required': False})
                   for row in METADATA)


def _populate_blocks(fixture, rows, material):
    support = material('stone')
    for row in rows:
        x, y, z = row['position']
        fixture.put((x, y - 1, z), support)
        fixture.put(row['position'], material(row['name']))


def _populate_fans(fixture, rows, material):
    support = material('stone')
    for row in rows:
        fixture.put(row['support'], support)
        if row['control'] == 'air':
            continue
        value = support if row['control'] == 'stone' else material(row['name'], row['states'])
        fixture.put(row['position'], value)


def _populate_plants(fixture, rows, material):
    from .cell import AIR
    support, water = material('stone'), material('water', {'liquid_depth': 0})
    for row in rows:
        x, y, z = row['position']
        plant = material(row['name'])
        front, back = plant, AIR
        if row['control'] == 'plant_water':
            back = water
        elif row['control'] == 'water_plant':
            front, back = water, plant
        fixture.put((x, y - 1, z), support)
        fixture.put(row['position'], front, back)


def populate(fixture, identity):
    from .debug_blueprints import material
    builders = {METADATA[0][0]: _populate_blocks, METADATA[1][0]: _populate_fans,
                METADATA[2][0]: _populate_plants}
    if identity not in builders:
        raise ValueError('Unknown coral review blueprint: ' + identity)
    builders[identity](fixture, CASES[identity], material)
    return fixture.finish()
