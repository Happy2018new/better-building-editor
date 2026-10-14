"""Plain and enchanted frame controls derived from versioned native payloads."""
from __future__ import unicode_literals
import base64
import json
import zlib
from . import item_contents_data as source
from .cell import make_cell
from .nbt_spatial import field_key, rebase, root_payload
from .visible_actor import compose_actor, entity_nbt

SCHEMA_VERSION = 2
IDENTITY = 'test.entities.item_contents'
ENCHANTMENT = (9, 3)
METADATA = (IDENTITY, 'entities', 'Block Entities - Enchanted Items',
            (24, 8, 18), 'minecraft:frame')
ORIENTATION_IDENTITY = 'test.entities.item_orientations'
ORIENTATION_METADATA = (ORIENTATION_IDENTITY, 'entities', 'Block Entities - Item Orientations',
                        (44, 8, 64), 'minecraft:glow_frame')
PAIRS = (
    {'id': 'frame', 'source_case': 'frame_filled',
     'plain': (3, 2, 3), 'enchanted': (10, 2, 3), 'empty': (17, 2, 3)},
    {'id': 'glow_frame', 'source_case': 'glow_frame_filled',
     'plain': (3, 2, 10), 'enchanted': (10, 2, 10), 'empty': (17, 2, 10)},
)
VISUAL_CASE = {
    'schema': SCHEMA_VERSION, 'fixture': IDENTITY, 'pairs': PAIRS,
    'modes': ('editor', 'full', 'missing'),
    'camera': {'editor': (180., 20., 1.6), 'world_offset': (0., 6., -28.)},
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
ORIENTATION_CASES = tuple({'id': '%s_f%d_r%d' % (kind, facing, rotation),
    'source_case': kind+'_filled', 'facing': facing, 'rotation_degrees': rotation*45.,
    'plain': (3+rotation*5, 2, 3+(facing+family*6)*5),
    'enchanted': (5+rotation*5, 2, 3+(facing+family*6)*5)}
    for family, kind in enumerate(('frame', 'glow_frame'))
    for facing in range(6) for rotation in range(8))
ORIENTATION_VISUAL_CASE = {
    'schema': 1, 'fixture': ORIENTATION_IDENTITY, 'cases': ORIENTATION_CASES,
    'modes': ('editor', 'full', 'missing'), 'minimum_temporal_frames': 3,
    'native_source_sha256': source.PROBE_SHA256,
    'item_content_accepted': False, 'enchantment_glint_accepted': False,
    'requirements': ('All six faces and eight rotations use the same observed item payload',
                     'Inspect body, animated highlight, support depth and partial occupancy separately'),
}

CATALOGUE_SIZE = (64, 8, 40)
CATALOGUE_PAGE_SIZE = 24


def _item_catalogue():
    from . import item_icon_data as icons
    keys = sorted(icons.ITEMS)
    result = []
    for start in range(0, len(keys), CATALOGUE_PAGE_SIZE):
        number = start // CATALOGUE_PAGE_SIZE + 1
        identity = 'test.entities.item_catalogue.%02d' % number
        rows = tuple({'id': '%s:%d' % key, 'item': key,
                      'plain': (3 + offset % 5 * 12, 3, 3 + offset // 5 * 7),
                      'enchanted': (7 + offset % 5 * 12, 3, 3 + offset // 5 * 7)}
                     for offset, key in enumerate(keys[start:start + CATALOGUE_PAGE_SIZE]))
        metadata = (identity, 'entities', '\u7269\u54c1\u56fe\u6807\u76ee\u5f55 \u00b7 %02d' % number,
                    CATALOGUE_SIZE, 'minecraft:frame')
        result.append((metadata, rows))
    return tuple(result)


CATALOGUE = _item_catalogue()
CATALOGUE_METADATA = tuple(row[0] for row in CATALOGUE)
CATALOGUE_CASES = dict((metadata[0], rows) for metadata, rows in CATALOGUE)
CATALOGUE_VISUAL_CASES = dict((identity, {
    'schema': 1, 'fixture': identity, 'cases': rows,
    'modes': ('editor', 'full', 'missing'), 'minimum_temporal_frames': 3,
    'source': 'Measured engine item IDs/icons in the native frame compound template',
    'content_accepted': False, 'enchantment_accepted': False,
}) for identity, rows in CATALOGUE_CASES.items())


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


def populate_orientations(fixture):
    from .debug_appearance_blueprints import observations
    from .debug_blueprints import material
    rows = dict((row['case'], row) for row in observations())
    enchanted = dict((row['case'], row) for row in enchanted_observations())
    normals = ((0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0))
    fixture.floor()
    for case in ORIENTATION_CASES:
        row = rows[case['source_case']]
        value = material(row['block']['name'], {'facing_direction': case['facing']})
        for mode in ('plain', 'enchanted'):
            position = case[mode]
            native = enchanted[case['source_case']] if mode == 'enchanted' else row
            actor = _actor(native, position, mode)
            root = root_payload(entity_nbt(actor))
            root[field_key(root, 'ItemRotation')]['__value__'] = case['rotation_degrees']
            support = tuple(position[axis]-normals[case['facing']][axis] for axis in range(3))
            fixture.plinth(position)
            fixture.put(support, material('stone'))
            fixture.document.blocks[position] = make_cell(value, nbt=actor)
    return fixture.finish()


def populate_catalogue(fixture, identity):
    from .debug_appearance_blueprints import observations
    from .debug_blueprints import material
    rows = dict((row['case'], row) for row in observations())
    native = dict((row['case'], row) for row in enchanted_observations())
    fixture.floor()
    for index, case in enumerate(CATALOGUE_CASES[identity]):
        kind = 'frame' if index % 2 == 0 else 'glow_frame'
        source_case = kind + '_filled'
        block = material(kind, {'facing_direction': 2})
        for mode in ('plain', 'enchanted'):
            position = case[mode]
            source_row = native[source_case] if mode == 'enchanted' else rows[source_case]
            actor = _actor(source_row, position, mode)
            root = root_payload(entity_nbt(actor))
            item = root_payload(root[field_key(root, 'Item')])
            item[field_key(item, 'Name')]['__value__'] = case['item'][0]
            item[field_key(item, 'Damage')]['__value__'] = case['item'][1]
            root[field_key(root, 'ItemRotation')]['__value__'] = 0.
            fixture.plinth(position)
            fixture.put((position[0], position[1], position[2]+1), material('stone'))
            fixture.document.blocks[position] = make_cell(block, nbt=actor)
    return fixture.finish()


def orientation_document(case_id):
    """Near-view controls retain the public fixture's exact facing and item NBT."""
    from .debug_blueprints import build
    from .cell import rebase
    from .model import Document
    case = next((row for row in ORIENTATION_CASES if row['id'] == case_id), None)
    if case is None:
        raise ValueError('Unknown public item orientation case')
    source = build(ORIENTATION_IDENTITY)
    result = Document((8, 8, 8), name=source.name, biome=source.biome)
    normal = ((0,-1,0),(0,1,0),(0,0,-1),(0,0,1),(-1,0,0),(1,0,0))[case['facing']]
    targets = ((3,3,2),(3,3,5)) if case['facing'] in (4,5) else ((2,3,3),(5,3,3))
    for mode, target in zip(('plain','enchanted'), targets):
        original = case[mode]
        delta = tuple(target[axis] - original[axis] for axis in range(3))
        for shift in ((0,0,0), tuple(-value for value in normal)):
            position = tuple(original[axis]+shift[axis] for axis in range(3))
            destination = tuple(target[axis]+shift[axis] for axis in range(3))
            result.set_cell(destination, rebase(source.get(position), delta))
    return result


def catalogue_document(identity, case_id):
    """Near-view cases preserve the public fixture's exact typed item payload."""
    from .debug_blueprints import build
    from .cell import rebase
    from .model import Document
    row = next((value for value in CATALOGUE_CASES[identity] if value['id'] == case_id), None)
    if row is None:
        raise ValueError('Unknown public item catalogue case')
    source = build(identity)
    result = Document((11, 6, 5), name=source.name, biome=source.biome)
    for mode, target in (('plain', (2, 3, 2)), ('enchanted', (5, 3, 2))):
        old = row[mode]
        delta = tuple(target[axis] - old[axis] for axis in range(3))
        for shift in ((0, 0, 0), (0, 0, 1), (0, -1, 0)):
            original = tuple(old[axis] + shift[axis] for axis in range(3))
            destination = tuple(target[axis] + shift[axis] for axis in range(3))
            result.set_cell(destination, rebase(source.get(original), delta))
    return result


SLOT_IDENTITY = 'test.entities.visible_item_slots'
SLOT_METADATA = (SLOT_IDENTITY, 'entities', '\u53ef\u89c1\u7269\u54c1\u69fd\u4f4d',
                 (40, 8, 24), 'minecraft:oak_shelf')
SLOT_CASES = tuple({'id': family+'.'+mode, 'family': family, 'mode': mode,
                   'position': (3+index % 6*6, 3, 3+index//6*8)}
                  for index, (family, mode) in enumerate((
                      ('shelf', 'empty'), ('shelf', 'center'), ('shelf', 'left'),
                      ('shelf', 'right'), ('shelf', 'three'), ('campfire', 'empty'),
                      ('campfire', 'one'), ('campfire', 'two'), ('campfire', 'four'),
                      ('lectern', 'empty'), ('lectern', 'book'))))
SLOT_VISUAL_CASE = {'schema': 1, 'fixture': SLOT_IDENTITY, 'cases': SLOT_CASES,
                    'modes': ('editor', 'full', 'missing'), 'content_accepted': False,
                    'source': 'Native 3.10 item-use compounds; left/right shelf cases reorder the measured center item'}


def slot_observations():
    from . import visible_item_slot_data as source_slots
    if source_slots.SCHEMA_VERSION != 1 or source_slots.ENGINE_VERSION != '3.10.0.420447':
        raise ValueError('Visible item slots require target-version native observations')
    return json.loads(zlib.decompress(base64.b64decode(source_slots.ROWS)))


def populate_slots(fixture):
    from .cell import thaw, freeze
    from .debug_blueprints import material
    from .visible_item_contents import content_slots
    rows = dict((row['name'], row) for row in slot_observations())
    fixture.floor()
    for case in SLOT_CASES:
        name = {'shelf': 'minecraft:oak_shelf', 'campfire': 'minecraft:campfire',
                'lectern': 'minecraft:lectern'}[case['family']]
        row, position = rows[name], case['position']
        root = rebase(row['before'] if case['mode'] == 'empty' else row['after'],
                      tuple(position[axis]-row['pos'][axis] for axis in range(3)))
        if case['family'] == 'shelf' and case['mode'] not in ('empty', 'center'):
            entries = root[field_key(root, 'Items')]
            empty, full = entries[0], entries[1]
            indices = {'left': (0,), 'right': (2,), 'three': (0,1,2)}[case['mode']]
            root[field_key(root, 'Items')] = [thaw(freeze(full if index in indices else empty))
                                               for index in range(3)]
        elif case['family'] == 'campfire' and case['mode'] in ('one', 'two'):
            for index in range(2 if case['mode'] == 'two' else 1, 4):
                root.pop(field_key(root, 'Item%d' % (index+1)))
        block = material(name)
        actor = compose_actor({}, root)
        if content_slots(block, actor, '3.10.0.420447') is None:
            raise ValueError('Public visible item slot fixture association is invalid')
        fixture.plinth(position)
        fixture.document.blocks[position] = make_cell(block, nbt=actor)
    return fixture.finish()


def slot_document(case_id):
    from .cell import rebase
    from .debug_blueprints import build
    from .model import Document
    row = next((value for value in SLOT_CASES if value['id'] == case_id), None)
    if row is None:
        raise ValueError('Unknown public content slot case')
    source = build(SLOT_IDENTITY)
    result = Document((8, 8, 8), name=source.name, biome=source.biome)
    for shift in ((0,0,0), (0,-1,0)):
        position = tuple(row['position'][axis]+shift[axis] for axis in range(3))
        target = tuple((3,3,3)[axis]+shift[axis] for axis in range(3))
        result.set_cell(target, rebase(source.get(position),
                                      tuple(target[axis]-position[axis] for axis in range(3))))
    return result
