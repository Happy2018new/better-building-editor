"""Plain and enchanted frame controls derived from versioned native payloads."""
from __future__ import unicode_literals
import base64
import json
import zlib
from . import item_contents_data as source
from .cell import make_cell
from .nbt_spatial import field_key, rebase, root_payload
from .visible_actor import compose_actor

SCHEMA_VERSION = 2
IDENTITY = 'test.entities.item_contents'
ENCHANTMENT = (9, 3)
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
    'source_kind': 'Native inventory-enchanted swords inserted by block interaction',
    'native_enchanted_payload_verified': True,
    'native_enchanted_source_sha256': source.PROBE_SHA256,
    'native_source_build_directory': source.NATIVE_BUILD_DIRECTORY_VERSION,
    'native_runtime_version': source.NATIVE_RUNTIME_VERSION,
    'native_runtime_version_verified': source.NATIVE_RUNTIME_VERIFIED,
    'item_content_accepted': False, 'enchantment_glint_accepted': False,
    'requirements': (
        'Native item data is verified; editor, projection and glint pixels remain independent',
        'Compare ordinary and enchanted items with the empty-frame control',
        'Verify moving glint inside the item silhouette in fresh temporal frames',
        'Verify opacity, clipping, occupancy, item replacement and resource cleanup',
    ),
    'unverified_families': ('shelf_item_slots',),
}


def enchanted_observations():
    from . import block_registry as registry
    if (source.SCHEMA_VERSION != 2 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native enchanted item fixtures need regeneration for this registry')
    rows = json.loads(zlib.decompress(base64.b64decode(source.ROWS)))
    if tuple(row['case'] for row in rows) != tuple(pair['source_case'] for pair in PAIRS):
        raise ValueError('Native enchanted item fixture associations need updating')
    return rows


def _actor(row, position, mode):
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
    return compose_actor({}, data)


def populate(fixture):
    from . import block_registry as registry
    from .debug_appearance_blueprints import observations
    from .debug_blueprints import material
    from .entity_overlays import frame_item
    rows = dict((row['case'], row) for row in observations())
    enchanted = dict((row['case'], row) for row in enchanted_observations())
    prepared = []
    normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1),
               (0, 0, 1), (-1, 0, 0), (1, 0, 0))
    for pair in PAIRS:
        row = rows[pair['source_case']]
        value = row['block']['name'], row['block']['aux']
        facing = registry.states(value)['facing_direction']
        for mode in ('plain', 'enchanted', 'empty'):
            position = pair[mode]
            source_row = enchanted[pair['source_case']] if mode == 'enchanted' else row
            if source_row['block'] != row['block']:
                raise ValueError('Native frame item source states need updating')
            actor = _actor(source_row, position, mode)
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
