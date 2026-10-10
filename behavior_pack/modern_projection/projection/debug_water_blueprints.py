# -*- coding: utf-8 -*-
"""Public source/flow/state fixtures, shared by editor and live acceptance."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import background, edit_cell, foreground
from .water_interaction_data import WATER_SENSITIVE_BLOCKS

METADATA = ('test.layers.water_behaviors', 'layers', '水源、流水与熄灭',
            (48, 8, 64), 'minecraft:campfire')
_EXTRA = ('oak_fence', 'oak_stairs', 'oak_slab', 'rail', 'white_carpet', 'web',
          'cocoa', 'leaf_litter', 'pink_petals', 'wildflowers', 'snow_layer')
NAMES = tuple(sorted(WATER_SENSITIVE_BLOCKS)) + tuple('minecraft:' + name for name in _EXTRA)
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': (8, 8, 8), 'focus': (3, 3, 3),
    'projection_height': 20,
    'camera': {'editor': (35., 25., 2.8), 'world_offset': (-3.5, 3., -5.)},
    'cells': tuple({'key': name.split(':')[-1], 'name': name,
                    'dry': (3 + index % 6 * 7, 1, 3 + index // 6 * 7),
                    'source': (5 + index % 6 * 7, 1, 3 + index // 6 * 7),
                    'flow': (7 + index % 6 * 7, 1, 3 + index // 6 * 7)}
                   for index, name in enumerate(NAMES)),
}


def dry_state(name):
    value = (name, registry.DEFAULT_AUX[name])
    properties = registry.states(value)
    if 'lit' in properties:
        properties['lit'] = True
    if 'extinguished' in properties:
        properties['extinguished'] = False
    result = registry.from_states(name, properties)
    if result is None:
        raise ValueError('Missing native dry water-behaviour state: ' + name)
    return result


def populate(fixture):
    fixture.floor()
    source = registry.from_states('minecraft:water', {'liquid_depth': 0})
    flow = registry.from_states('minecraft:water', {'liquid_depth': 3})
    for row in VISUAL_CASE['cells']:
        dry = dry_state(row['name'])
        for key, value in (('dry', dry), ('source', edit_cell(dry, source, 2)),
                           ('flow', edit_cell(flow, dry, 2))):
            fixture.put(row[key], foreground(value), background(value))
        if row['name'] == 'minecraft:cocoa':
            for key in ('dry', 'flow'):
                x, y, z = row[key]
                fixture.put((x, y, z - 1), ('minecraft:jungle_log', registry.DEFAULT_AUX['minecraft:jungle_log']))
    return fixture.finish()
