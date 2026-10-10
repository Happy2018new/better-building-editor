"""Stable sign cases retaining observed two-sided native text and style tags."""
from __future__ import unicode_literals
from .cell import make_cell
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
VISUAL_CASE = {'schema':1,'fixture':IDENTITY,'cases':CASES,'isolated_size':(3,3,3),'focus':(1,1,1),
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
    return fixture.finish()
