# -*- coding: utf-8 -*-
"""Public pure-liquid states and neighbor sources; visual acceptance is pending."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import AIR

METADATA = ('test.layers.liquids', 'layers', '\u7eaf\u6db2\u4f53\u72b6\u6001',
            (64, 8, 64), 'minecraft:water')
NAMES = ('minecraft:water', 'minecraft:flowing_water',
         'minecraft:lava', 'minecraft:flowing_lava')
LAYERS = ('foreground', 'background')


def _native_value(name, depth):
    properties = registry.states((name, registry.DEFAULT_AUX[name]))
    properties['liquid_depth'] = depth
    value = registry.from_states(name, properties)
    if value is None:
        raise ValueError('Missing native liquid state: %s %r' % (name, properties))
    return value


def _state_rows():
    rows = []
    for name in NAMES:
        values = sorted(((registry.states((name, aux)), (name, aux))
                         for aux in registry.aux_values(name)),
                        key=lambda item: (item[0]['liquid_depth'], item[1][1]))
        for properties, value in values:
            index = len(rows)
            x, z = 2 + index % 16 * 4, 4 + index // 16 * 12
            rows.append({'id': name.split(':')[1] + '_depth_' + str(properties['liquid_depth']),
                         'name': name, 'value': value, 'states': properties,
                         'foreground': (x, 3, z), 'background': (x, 3, z + 4)})
    return tuple(rows)


def _case(identity, kind, layer, liquids, extra_supports=()):
    keep = liquids[0][0]
    targets = tuple(pos for pos, unused in liquids)
    target_set = set(targets)
    supports = set((pos[0], pos[1] - 1, pos[2]) for pos in targets)
    supports.update(extra_supports)
    supports = tuple(sorted(supports - target_set))
    return {'id': identity + '_' + LAYERS[layer], 'kind': kind, 'layer': layer,
            'keep': keep, 'cells': targets, 'liquid_cells': tuple(liquids),
            'supports': supports,
            'controls': {
                'supported_positive': {'keep': targets + supports, 'remove': ()},
                'supported_negative': {'keep': supports, 'remove': targets},
                'liquid_only': {'keep': targets, 'remove': supports},
                'empty': {'keep': (), 'remove': targets + supports},
            }}


def _state_cases(rows):
    return tuple(_case(row['id'], 'state', layer, ((row[name], row['value']),))
                 for row in rows for layer, name in enumerate(LAYERS))


def _neighbor_cases():
    rows = []
    # Depths are semantic states, resolved by the current registry, never aux math.
    shapes = (
        ('source_pair', (((0, 0, 0), False, 0), ((1, 0, 0), False, 0))),
        ('flow_gradient', (((0, 0, 0), False, 0), ((1, 0, 0), True, 1),
                           ((2, 0, 0), True, 3), ((3, 0, 0), True, 7))),
        ('flow_corner', (((0, 0, 0), True, 3), ((-1, 0, 0), False, 0),
                         ((0, 0, -1), True, 1), ((1, 0, 0), True, 7),
                         ((-1, 0, -1), False, 0))),
        ('falling_column', (((0, 0, 0), True, 8), ((0, 1, 0), True, 8),
                            ((0, 2, 0), True, 8))),
        ('liquid_above', (((0, 0, 0), True, 3), ((0, 1, 0), True, 8))),
        ('solid_side', (((0, 0, 0), True, 3),)),
        ('source_pool', (((0, 0, 0), False, 0), ((1, 0, 0), False, 0),
                         ((0, 0, 1), False, 0), ((1, 0, 1), False, 0))),
        ('falling_to_flow', (((0, 0, 0), True, 8), ((0, 1, 0), True, 8),
                             ((1, 0, 0), True, 3), ((2, 0, 0), True, 7))),
    )
    for family_index, family in enumerate(('water', 'lava')):
        for layer in range(len(LAYERS)):
            z = 50 + (family_index * 2 + layer) * 4
            for index, (kind, shape) in enumerate(shapes):
                keep = (3 + index * 8, 3, z)
                liquids = tuple((tuple(keep[i] + offset[i] for i in range(3)),
                                 _native_value('minecraft:' + ('flowing_' if flowing else '') + family,
                                               depth)) for offset, flowing, depth in shape)
                extra = ((keep[0] + 1, keep[1], keep[2]),) if kind == 'solid_side' else ()
                rows.append(_case(family + '_' + kind, kind, layer, liquids, extra))
    return tuple(rows)


STATES = _state_rows()
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'registry_version': registry.source_version(),
    'registry_fingerprint': registry.fingerprint(), 'states': STATES,
    'cases': _state_cases(STATES) + _neighbor_cases(),
    'size': (10, 8, 10), 'focus': (3, 3, 3), 'projection_height': 20,
    'camera': {'editor': (35., 25., 4.6), 'world_offset': (-5., 4., -7.)},
    'modes': ('full', 'missing'), 'native_resolution': True,
    'acceptance': {'editor': 'pending', 'projection_full': 'pending',
                   'projection_missing': 'pending'},
    'mask': {
        'positive_control': 'liquid_only', 'negative_control': 'empty',
        'supported_pair': ('supported_positive', 'supported_negative'),
        'target_cells': 'cells', 'excluded_cells': 'supports',
        'require_native_liquid_pixels': True,
        'require_liquid_only_pixels': True,
        'require_supported_difference_pixels': True,
        'support_pixels_can_satisfy_gate': False,
        'fixed_cell_hull_height': 1.,
    },
    'native_shape_acceptance': 'pending_four_corner_heights_and_neighbor_faces',
}


def populate(fixture):
    stone = ('minecraft:stone', registry.DEFAULT_AUX['minecraft:stone'])
    for row in VISUAL_CASE['cases']:
        for pos in row['supports']:
            fixture.put(pos, stone)
        for pos, value in row['liquid_cells']:
            fixture.put(pos, value if row['layer'] == 0 else AIR,
                        value if row['layer'] == 1 else AIR)
    return fixture.finish()


def source_document(identity, isolated=False, control='supported_positive'):
    """Extract one public source with exact layers and independently held supports."""
    from .debug_blueprints import build
    from .model import Document
    row = next((item for item in VISUAL_CASE['cases'] if item['id'] == identity), None)
    if row is None:
        raise ValueError('Unknown pure-liquid visual case: ' + identity)
    if control not in row['controls']:
        raise ValueError('Unknown pure-liquid visual control: ' + control)
    source = build(METADATA[0])
    result = Document(VISUAL_CASE['size'] if isolated else source.size, name=source.name,
                      biome=source.biome)
    delta = (tuple(VISUAL_CASE['focus'][i] - row['keep'][i] for i in range(3))
             if isolated else (0, 0, 0))
    for pos in row['controls'][control]['keep']:
        target = tuple(pos[i] + delta[i] for i in range(3))
        result.set_cell(target, source.get(pos))
    return result
