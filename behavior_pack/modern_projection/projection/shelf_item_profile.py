"""Two exact shelf items; body scope and plain/glint acceptance are independent."""
from . import block_registry
from . import item_icon_data as icons
from . import item_sprite_data as transport
from . import shelf_item_data as source

ITEMS = frozenset((('minecraft:apple', 0), ('minecraft:diamond_sword', 0)))
ENCHANTMENTS = frozenset((('minecraft:diamond_sword', 0),))


def candidate_items(engine_version):
    if (source.SCHEMA_VERSION != 1 or icons.SCHEMA_VERSION != 1 or icons.LAYOUT_VERSION != 1 or
            engine_version != source.ENGINE_VERSION or engine_version != icons.ENGINE_VERSION or
            transport.PALETTE_SHA256 != block_registry.fingerprint()):
        raise ValueError('Shelf items need the exact measured engine, palette and icon layout')
    result = {}
    for key in ITEMS:
        row = dict(icons.ITEMS[key])
        if row.get('resource_key') != key or 'shelf' not in row.get('content_families', ('frame', 'shelf', 'campfire')):
            raise ValueError('Shelf item resources exceed the two observed item pairs')
        row.update(content_families=('shelf',), observed_aux=(0,), max_durability=0,
                   enchantment_qualified=key in ENCHANTMENTS)
        result[key] = row
    return result


def production_items(engine_version):
    if engine_version != source.ENGINE_VERSION or not source.PRODUCTION_QUALIFIED:
        return {}
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest) or
            source.QUALIFICATION_RESOURCE_SHA256 != icons.RESOURCE_SHA256 or
            not source.QUALIFIED_ITEMS or not set(source.QUALIFIED_ITEMS) <= ITEMS or
            not set(source.QUALIFIED_ENCHANTMENTS) <= ENCHANTMENTS & set(source.QUALIFIED_ITEMS)):
        raise ValueError('Shelf deployment needs its own exact resource, plain and glint acceptance')
    candidates = candidate_items(engine_version)
    result = {}
    for key in source.QUALIFIED_ITEMS:
        row = dict(candidates[key])
        row['enchantment_qualified'] = key in source.QUALIFIED_ENCHANTMENTS
        result[key] = row
    return result
