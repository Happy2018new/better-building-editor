"""Public portal shapes, adjacent surfaces and native Nether portal controls."""
from __future__ import unicode_literals

METADATA = ('test.dynamic.portals', 'entities', '\u4f20\u9001\u95e8\u52a8\u6001\u8868\u9762',
            (16, 8, 16), 'minecraft:end_portal_frame')
POSITIONS = {'end_portal': ((2, 2, 2), (3, 2, 2), (2, 2, 3), (3, 2, 3)),
             'end_gateway': ((8, 2, 2), (9, 2, 2), (8, 3, 2)),
             'portal_x': ((2, 2, 9), (3, 2, 9), (2, 3, 9), (3, 3, 9)),
             'portal_z': ((9, 2, 9), (9, 2, 10), (9, 3, 9), (9, 3, 10))}
VISUAL_CASE = {'schema': 1, 'fixture': METADATA[0], 'positions': POSITIONS,
               'source_engine': '3.10.0.420447',
               'camera': {'editor': (35., 35., 2.)},
               'snapshot_only': True, 'particles': False}
ISOLATED_SIZE = (8, 8, 8)
FOCUS = (3, 3, 3)


def populate(fixture):
    from .debug_blueprints import material
    for family, positions in POSITIONS.items():
        for position in positions:
            native_name = 'portal' if family.startswith('portal_') else family
            properties = {'portal_axis': family[-1]} if native_name == 'portal' else None
            entity = ('EndPortal' if family == 'end_portal' else
                      'EndGateway' if family == 'end_gateway' else None)
            fixture.put(position, material(native_name, properties), entity=entity)
            if position[1] == 2:
                fixture.put((position[0], 1, position[2]), material('stone'))
    fixture.put((5, 2, 2), material('end_portal_frame', {'end_portal_eye_bit': True}))
    fixture.put((5, 1, 2), material('stone'))
    return fixture.finish()


def source_document(family):
    """Focused views derive all cells and actor data from the public gallery."""
    from .debug_blueprints import build
    from .model import Document
    from .nbt_spatial import rebase
    from .cell import make_cell, foreground, background, actor_data
    if family not in POSITIONS:
        raise ValueError('Unknown public portal case: '+str(family))
    source=build(METADATA[0])
    anchor=POSITIONS[family][0]
    delta=tuple(FOCUS[axis]-anchor[axis] for axis in range(3))
    document=Document(ISOLATED_SIZE,name=source.name,biome=source.biome)
    for position in POSITIONS[family]:
        target=tuple(position[axis]+delta[axis] for axis in range(3))
        cell=source.get(position)
        document.set_cell(target,make_cell(foreground(cell),background(cell),
                          nbt=rebase(actor_data(cell),delta)))
        if position[1]==2:
            support=(position[0],position[1]-1,position[2])
            document.set_cell(tuple(support[axis]+delta[axis] for axis in range(3)),source.get(support))
    return document
