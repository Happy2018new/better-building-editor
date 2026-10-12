"""Plain and enchanted frame controls derived from versioned native payloads."""
from __future__ import unicode_literals
from .cell import make_cell
from .nbt_spatial import field_key, rebase, root_payload
from .visible_actor import compose_actor

SCHEMA_VERSION = 1
IDENTITY = 'test.entities.item_contents'
METADATA = (IDENTITY, 'entities', 'Block Entities - Enchanted Items',
            (24, 8, 18), 'minecraft:frame')
PAIRS = (
    {'id': 'frame', 'source_case': 'frame_filled',
     'plain': (3, 2, 3), 'enchanted': (10, 2, 3), 'empty': (17, 2, 3)},
    {'id': 'glow_frame', 'source_case': 'glow_frame_filled',
     'plain': (3, 2, 10), 'enchanted': (10, 2, 10), 'empty': (17, 2, 10)},
)
VISUAL_CASE = {
    'schema': SCHEMA_VERSION, 'fixture': IDENTITY, 'pairs': PAIRS,
    'modes': ('editor', 'full', 'missing'),
    'minimum_temporal_frames': 3,
    'source_kind': 'Observed filled-frame payloads with a synthetic typed sharpness tag',
    'native_enchanted_payload_verified': False,
    'item_content_accepted': False, 'enchantment_glint_accepted': False,
    'requirements': (
        'Independently verify native placed-frame item NBT before pixel acceptance',
        'Compare ordinary and enchanted items with the empty-frame control',
        'Verify moving glint inside the item silhouette in fresh temporal frames',
        'Verify opacity, clipping, occupancy, item replacement and resource cleanup',
    ),
    'unverified_families': ('shelf_item_slots',),
}


def _actor(row, position, mode):
    from .debug_blueprints import tag
    source_cell = row['cell_nbt'][0]
    delta = tuple(position[axis] - source_cell['pos'][axis] for axis in range(3))
    data = rebase(source_cell['nbt'], delta)
    root = root_payload(data)
    item_key = field_key(root, 'Item')
    item = root_payload(root.get(item_key))
    if item is None:
        raise ValueError('Native item blueprint needs an observed filled frame')
    if mode == 'empty':
        root.pop(item_key)
    elif mode == 'enchanted':
        key = field_key(item, 'tag')
        if key is None:
            key = 'tag'
            item[key] = {}
        user_data = root_payload(item[key])
        if user_data is None:
            raise ValueError('Native frame item compound needs a verified schema')
        # EnchantType.WeaponDamage is 9; keep the native Short/List tag types.
        user_data[field_key(user_data, 'ench') or 'ench'] = tag([
            {'id': tag(9, 2), 'lvl': tag(3, 2)}], 9)
    return compose_actor({}, data)


def populate(fixture):
    from . import block_registry as registry
    from .debug_appearance_blueprints import observations
    from .debug_blueprints import material
    from .entity_overlays import frame_item
    rows = dict((row['case'], row) for row in observations())
    prepared = []
    normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1),
               (0, 0, 1), (-1, 0, 0), (1, 0, 0))
    for pair in PAIRS:
        row = rows[pair['source_case']]
        value = row['block']['name'], row['block']['aux']
        facing = registry.states(value)['facing_direction']
        for mode in ('plain', 'enchanted', 'empty'):
            position = pair[mode]
            actor = _actor(row, position, mode)
            item = frame_item(value, actor)
            if ((mode == 'empty' and item is not None) or
                    (mode != 'empty' and (item is None or
                     item['isEnchanted'] != (mode == 'enchanted')))):
                raise ValueError('Native frame item fixture association needs updating')
            support = tuple(position[axis] - normals[facing][axis] for axis in range(3))
            prepared.append((position, support, value, actor))
    fixture.floor()
    for position, support, value, actor in prepared:
        fixture.plinth(position)
        fixture.put(support, material('stone'))
        fixture.document.blocks[position] = make_cell(value, nbt=actor)
    return fixture.finish()
