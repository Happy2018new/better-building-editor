"""Small public galleries tied to the compatibility inventory's source data."""
from __future__ import unicode_literals

from . import block_registry as registry
from .cell import AIR, rebase
from .entity_defaults_data import DEFAULTS
from .model import Document

SCHEMA_VERSION = 1
PAGE_SIZE = (32, 8, 42)
ISOLATED_SIZE = (8, 8, 8)
FOCUS = (3, 3, 3)

DYNAMIC_FAMILIES = (
    ('fluids', '\u6d41\u4f53\u4e0e\u4f20\u9001\u95e8',
     ('water', 'flowing_water', 'lava', 'flowing_lava', 'bubble_column',
      'cauldron', 'portal', 'end_portal', 'end_gateway', 'end_portal_frame')),
    ('fire', '\u706b\u7130\u4e0e\u70b9\u71c3\u72b6\u6001',
     ('fire', 'soul_fire', 'campfire', 'soul_campfire', 'lit_blast_furnace', 'lit_smoker')),
    ('lanterns', '\u706f\u7b3c',
     ('lantern', 'soul_lantern', 'copper_lantern', 'exposed_copper_lantern',
      'weathered_copper_lantern', 'oxidized_copper_lantern', 'waxed_copper_lantern',
      'waxed_exposed_copper_lantern', 'waxed_weathered_copper_lantern',
      'waxed_oxidized_copper_lantern')),
    ('sculk', '\u5e7d\u533f',
     ('sculk', 'sculk_vein', 'sculk_sensor', 'calibrated_sculk_sensor',
      'sculk_catalyst', 'sculk_shrieker')),
    ('aquatic', '\u6c34\u751f\u690d\u7269\u4e0e\u6d77\u6676\u77f3',
     ('kelp', 'seagrass', 'firefly_bush', 'prismarine', 'prismarine_slab',
      'prismarine_double_slab', 'prismarine_stairs', 'prismarine_wall', 'sea_lantern')),
    ('nether', '\u4e0b\u754c\u7eb9\u7406',
     ('crimson_stem', 'crimson_hyphae', 'warped_stem', 'warped_hyphae',
      'magma', 'respawn_anchor')),
    ('special', '\u7279\u6b8a\u672c\u4f53\u4e0e\u4e66\u672c',
     ('command_block', 'chain_command_block', 'repeating_command_block',
      'stonecutter_block', 'enchanting_table', 'lectern', 'conduit', 'beacon',
      'mob_spawner', 'trial_spawner', 'vault', 'big_dripleaf')),
)


def _dynamic_rows(names):
    rows = []
    for short_name in names:
        name = 'minecraft:' + short_name
        default = registry.DEFAULT_AUX[name]
        alternatives = registry.aux_values(name)
        for variant, aux in (('default', default), ('state', alternatives[-1])):
            if variant == 'state' and aux == default:
                continue
            rows.append({'id': short_name + '.' + variant, 'material': (name, aux),
                         'name': name, 'variant': variant})
    return _anchors(rows)


def _anchors(rows):
    return tuple(dict(row, anchor=(3 + index % 5 * 6, 3, 3 + index // 5 * 6))
                 for index, row in enumerate(rows))


def _catalogue():
    from .entity_defaults import material
    result = []
    for family, title, names in DYNAMIC_FAMILIES:
        identity = 'test.dynamic.' + family
        metadata = (identity, 'registry', '\u52a8\u6001\u5916\u89c2 \u00b7 ' + title,
                    PAGE_SIZE, 'minecraft:' + names[0])
        result.append((metadata, _dynamic_rows(names)))
    names = sorted(DEFAULTS)
    for start in range(0, len(names), 24):
        number = start // 24 + 1
        identity = 'test.entities.catalogue.%02d' % number
        page = names[start:start + 24]
        metadata = (identity, 'entities', 'NBT\u5168\u89c8 \u00b7 %02d' % number,
                    PAGE_SIZE, page[0])
        rows = [{'id': name, 'name': name, 'variant': 'captured_default',
                 'material': material(name)} for name in page]
        result.append((metadata, _anchors(rows)))
    return tuple(result)


CATALOGUE = _catalogue()
METADATA = tuple(row[0] for row in CATALOGUE)
CASES = dict((metadata[0], rows) for metadata, rows in CATALOGUE)
VISUAL_CASES = dict((identity, {
    'schema': SCHEMA_VERSION, 'fixture': identity, 'cases': rows,
    'size': ISOLATED_SIZE, 'focus': FOCUS,
    'modes': ('editor', 'projection_full', 'projection_missing'),
    'camera': {'editor': (35., 25., 3.), 'world_offset': (-3., 2., -4.)},
    'snapshot_only': True,
    'acceptance': {'complete_source_actor': True, 'visible_support_control': True,
                   'native_and_custom_owner_unique': True},
}) for identity, rows in CASES.items())


def populate(fixture, identity):
    from .debug_blueprints import material
    for row in CASES[identity]:
        fixture.plinth(row['anchor'], 'light_gray_concrete')
        fixture.group(row['anchor'], row['material'])
    return fixture.finish()


def source_document(identity, case_id):
    """Extract a public cell and reciprocal group with identical saved actor data."""
    from .block_groups import group_partner
    from .debug_blueprints import build
    rows = CASES.get(identity, ())
    row = next((item for item in rows if item['id'] == case_id), None)
    if row is None:
        raise ValueError('Unknown compatibility blueprint/case: ' + str((identity, case_id)))
    source = build(identity)
    result = Document(ISOLATED_SIZE, name=source.name, biome=source.biome)
    anchor = row['anchor']
    positions = [anchor, (anchor[0], anchor[1] - 1, anchor[2])]
    relationship = group_partner(row['material'])
    if relationship is not None:
        offset, unused = relationship
        positions.append(tuple(anchor[i] + offset[i] for i in range(3)))
    for position in positions:
        cell = source.get(position)
        if cell != AIR:
            target = tuple(FOCUS[i] + position[i] - anchor[i] for i in range(3))
            delta = tuple(target[i] - position[i] for i in range(3))
            result.set_cell(target, rebase(cell, delta))
    return result
