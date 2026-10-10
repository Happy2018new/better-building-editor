"""Stable sign cases retaining observed two-sided native text and style tags."""
from __future__ import unicode_literals
from .cell import AIR, actor_data, foreground, make_cell
from .nbt_spatial import root_payload, scalar, rebase
from .visible_actor import compose_actor
from .native_sign_data import SOURCE_VERSION, PALETTE_SHA256, OBSERVED_STYLES

SCHEMA_VERSION = 1
IDENTITY = 'test.entities.signs'
METADATA = (IDENTITY, 'entities', 'Block Entities - Two-Sided Signs', (16, 8, 10), 'minecraft:standing_sign')
CASES = (
    {'id':'standing_front_back','name':'minecraft:standing_sign','position':(3,1,3),'support':(3,0,3)},
    {'id':'hanging_front_back','name':'minecraft:oak_hanging_sign','position':(9,2,3),'support':(9,3,3)},
)
WET_CASES = tuple({'id': name, 'actor': (x, 1, 7), 'keep': (x + distance, 1, 7),
                  'cells': ((x, 1, 7), (x + distance, 1, 7)),
                  'supports': tuple((xx, yy, zz)
                                    for xx in range(x - 1, x + distance + 2)
                                    for yy in (0, 1) for zz in (6, 7, 8)
                                    if yy == 0 or (xx, yy, zz) not in
                                    ((x, 1, 7), (x + distance, 1, 7)))}
                 for name, x, distance in (('isolated', 3, 2), ('adjacent_water', 8, 1),
                                           ('fence_context', 12, 1)))
WET_VISUAL_CASE = {'schema': 1, 'fixture': IDENTITY, 'cases': WET_CASES,
                   'camera_offset': (0., .4, 4.), 'projection_height': 24,
                   'scope': 'Wet standing actor, independent dry control, adjacent water, and wet fence context'}
VISUAL_CASE = {'schema':3,'fixture':IDENTITY,'cases':CASES,'isolated_size':(3,3,3),'focus':(1,1,1),
               'world_text_roi':(.37,.28,.63,.69),
               'text_layout_tolerance':{'center':.10,'size':.20},
               'views':({'id':'front','editor':(0.,0.,3.),'world_offset':(0.,0.,2.3),'color':'green'},
                        {'id':'back','editor':(180.,0.,3.),'world_offset':(0.,0.,-2.3),'color':'red'})}


def populate(fixture):
    from . import block_registry as registry
    from .debug_blueprints import material
    if SOURCE_VERSION != registry.source_version() or PALETTE_SHA256 != registry.fingerprint():
        raise ValueError('Native sign blueprints need observations for this block registry')
    fixture.floor()
    for case in CASES:
        row = next(row for row in OBSERVED_STYLES if row['material'][0] == case['name'])
        root = root_payload(row['nbt'])
        origin = tuple(scalar(root, axis) for axis in ('x','y','z'))
        delta = tuple(case['position'][axis] - origin[axis] for axis in range(3))
        # Renderer fields are deliberately absent: the production adapter must
        # reconstruct both native text sides from the saved tagged payload.
        actor = compose_actor({}, rebase(row['nbt'], delta))
        fixture.document.blocks[case['position']] = make_cell(tuple(row['material']), nbt=actor)
        fixture.put(case['support'], material('stone'))
    base = fixture.document.get(CASES[0]['position'])
    water = material('water')
    for case in WET_CASES:
        wet = rebase(actor_data(base), tuple(case['actor'][i] - CASES[0]['position'][i]
                                           for i in range(3)))
        fixture.document.blocks[case['actor']] = make_cell(foreground(base), water, wet)
        if case['id'] == 'isolated':
            dry = rebase(actor_data(base), tuple(case['keep'][i] - CASES[0]['position'][i]
                                               for i in range(3)))
            fixture.document.blocks[case['keep']] = make_cell(foreground(base), AIR, dry)
        else:
            fixture.put(case['keep'], water if case['id'] == 'adjacent_water' else material('oak_fence'),
                        back=AIR if case['id'] == 'adjacent_water' else water)
        for pos in case['supports']:
            fixture.put(pos, material('stone' if pos[1] == 0 else 'glass'))
    return fixture.finish()
