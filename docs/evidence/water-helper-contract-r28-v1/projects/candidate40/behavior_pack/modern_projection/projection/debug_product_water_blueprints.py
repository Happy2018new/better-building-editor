"""Public water-style fixtures, independently usable by editor and world checks."""
from __future__ import unicode_literals

from . import block_registry as registry
from .cell import AIR, background, foreground, make_cell

METADATA = ('test.layers.water_style', 'layers', '\u6c34\u9762\u4e0e\u900f\u660e\u5ea6',
            (40, 8, 50), 'minecraft:water')
ISOLATED_SIZE = (10, 8, 10)
FOCUS = (3, 3, 3)


def _material(name, states=None):
    name = 'minecraft:' + name
    value = (name, registry.DEFAULT_AUX[name])
    if states is None:
        return value
    properties = registry.states(value)
    properties.update(states)
    result = registry.from_states(name, properties)
    if result is None:
        raise ValueError('Missing water fixture state: ' + name)
    return result


def _water(depth=0):
    return _material('water', {'liquid_depth': depth})


def _rows():
    shapes = [
        ('source', (((0, 0, 0), 0),)),
        ('low', (((0, 0, 0), 3),)),
        ('diagonal', (((0, 0, 0), 3), ((-1, 0, -1), 3))),
        ('drop_north', (((0, 0, 0), 0), ((0, -1, -1), 0))),
        ('pool', (((0, 0, 0), 0), ((1, 0, 0), 0),
                  ((0, 0, 1), 0), ((1, 0, 1), 0))),
        ('falling', (((0, 0, 0), 8), ((0, 1, 0), 8), ((1, 0, 0), 3))),
    ]
    for identity, step in (('flow_east', (1, 0, 0)), ('flow_south', (0, 0, 1)),
                           ('flow_west', (-1, 0, 0)), ('flow_north', (0, 0, -1))):
        shapes.append((identity, tuple((tuple(step[i] * offset for i in range(3)), depth)
                                       for offset, depth in ((-1, 0), (0, 3), (1, 7)))))
    rows = []
    for identity, shape in shapes:
        rows.append({'id': identity, 'shape': shape, 'body': None})
    for name in ('oak_fence', 'glass_pane', 'oak_slab', 'oak_stairs'):
        rows.append({'id': 'wet_' + name, 'shape': (((0, 0, 0), 0),), 'body': name})
    for name in ('oak_slab', 'oak_stairs', 'glass_pane', 'stone'):
        rows.append({'id': 'neighbor_' + name, 'shape': (((0, 0, 0), 0),),
                     'body': None, 'neighbors': (((0, 0, 1), name),)})
    rows.append({'id': 'transparent_overlap',
                 'shape': (((0, 0, 0), 0), ((0, 0, 2), 0)), 'body': None})
    return tuple(dict(row, anchor=(4 + index % 4 * 9, 3, 4 + index // 4 * 9))
                 for index, row in enumerate(rows))


CASES = _rows()
VISUAL_CASE = {
    'schema': 1, 'fixture': METADATA[0], 'size': ISOLATED_SIZE, 'focus': FOCUS,
    'registry_version': registry.source_version(), 'registry_fingerprint': registry.fingerprint(),
    'cases': CASES, 'controls': ('wet', 'dry', 'liquid_only', 'water_only', 'rearless', 'empty'),
    'modes': ('editor', 'projection_full', 'projection_missing'),
    'world_height_above_foot': 2,
    'camera': {'editor': (35., 25., 4.6), 'front': (0., 0., 3.),
               'world_offset': (6., 5., 8.)},
    'acceptance': {'style': 'java_snapshot_water_v1', 'native_parity_required': False,
                   'water_must_be_semitransparent': True},
}


def _cells(row):
    values = {}
    water_positions = set(offset for offset, unused in row['shape'])
    for offset, depth in row['shape']:
        support = (offset[0], offset[1] - 1, offset[2])
        if support not in water_positions:
            values[support] = _material('stone')
        values[offset] = _water(depth)
    if row['body'] is not None:
        values[(0, 0, 0)] = make_cell(_material(row['body']), _water())
        # Two cells back leaves the fluid's direct neighbor samples unchanged.
        values[(0, 0, -2)] = _material('gold_block')
    for offset, name in row.get('neighbors', ()):
        values[offset] = _material(name)
        values[(offset[0], offset[1] - 1, offset[2])] = _material('stone')
    return values


def populate(fixture):
    for row in CASES:
        anchor = row['anchor']
        for offset, value in _cells(row).items():
            pos = tuple(anchor[i] + offset[i] for i in range(3))
            fixture.put(pos, foreground(value), background(value))
    return fixture.finish()


def source_document(identity, control='wet'):
    """Extract exact public gallery cells; controls preserve supports and rear blocks."""
    from .debug_blueprints import build
    from .model import Document
    if identity == 'gallery':
        if control not in ('wet', 'dry'):
            raise ValueError('The public water gallery has only wet/dry controls')
        result = build(METADATA[0])
        if control == 'dry':
            for pos, value in list(result.blocks.items()):
                front, back = foreground(value), background(value)
                if front[0] in ('minecraft:water', 'minecraft:flowing_water'):
                    front = AIR
                if back[0] in ('minecraft:water', 'minecraft:flowing_water'):
                    back = AIR
                result.set_cell(pos, make_cell(front, back))
        return result
    row = next((item for item in CASES if item['id'] == identity), None)
    if row is None or control not in VISUAL_CASE['controls']:
        raise ValueError('Unknown product-water case/control: ' + str((identity, control)))
    source = build(METADATA[0])
    result = Document(ISOLATED_SIZE, name=source.name, biome=source.biome)
    liquid_positions = set(offset for offset, unused in row['shape'])
    for offset in _cells(row):
        if control in ('rearless', 'water_only', 'empty') and row['body'] and offset == (0, 0, -2):
            continue
        pos = tuple(row['anchor'][i] + offset[i] for i in range(3))
        value = source.get(pos)
        if offset in liquid_positions:
            if control == 'empty':
                continue
            if control == 'dry':
                value = make_cell(foreground(value) if row['body'] and offset == (0, 0, 0) else AIR)
            elif control in ('liquid_only', 'water_only'):
                value = make_cell(AIR, background(value)) if row['body'] and offset == (0, 0, 0) else value
        target = tuple(FOCUS[i] + offset[i] for i in range(3))
        result.set_cell(target, value)
    return result
