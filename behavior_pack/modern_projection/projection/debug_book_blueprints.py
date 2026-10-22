"""Small public book comparisons retain the established native actor payloads."""
from __future__ import unicode_literals

METADATA = (
    ('test.entities.book_enchanting', 'entities', '\u9644\u9b54\u53f0\u4e66\u00b7\u4f4d\u7f6e\u4e0e\u906e\u6321',
     (8, 6, 8), 'minecraft:enchanting_table'),
    ('test.entities.book_lectern', 'entities', '\u8bb2\u53f0\u4e66\u00b7\u7a7a\u53f0\u4e0e\u5e26\u4e66',
     (12, 6, 8), 'minecraft:lectern'),
)
VISUAL_CASES = {
    METADATA[0][0]: {'schema': 1, 'fixture': METADATA[0][0], 'focus': (3., 2.5, 3.),
                     'subjects': (('enchanting_table', (3, 2, 3)),), 'GPU_qualified': False},
    METADATA[1][0]: {'schema': 1, 'fixture': METADATA[1][0], 'focus': (5.5, 2.5, 3.),
                     'subjects': (('empty', (3, 2, 3)), ('book', (8, 2, 3))), 'GPU_qualified': False},
}


def populate(fixture, identity):
    from .debug_blueprints import material
    row = VISUAL_CASES[identity]
    if identity == METADATA[0][0]:
        position = row['subjects'][0][1]
        fixture.put((position[0], position[1] - 1, position[2]), material('cyan_concrete'))
        fixture.put(position, material('enchanting_table'), entity='EnchantTable')
    else:
        from .cell import make_cell
        from .debug_item_blueprints import slot_observations
        from .nbt_spatial import rebase
        from .visible_actor import compose_actor
        native = next(value for value in slot_observations() if value['name'] == 'minecraft:lectern')
        for mode, position in row['subjects']:
            fixture.put((position[0], position[1] - 1, position[2]), material('cyan_concrete'))
            payload = native['before'] if mode == 'empty' else native['after']
            delta = tuple(position[axis] - native['pos'][axis] for axis in range(3))
            actor = compose_actor({}, rebase(payload, delta))
            fixture.document.blocks[position] = make_cell(material('lectern'), nbt=actor)
    return fixture.finish()
