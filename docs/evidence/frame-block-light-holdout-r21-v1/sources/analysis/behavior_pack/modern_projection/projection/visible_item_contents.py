"""Observed content slots, independent of body rendering and item geometry.

Only the target-version structural samples are recognized. Unknown payloads
remain opaque; callers never infer inventory slots from transient render data.
"""
from collections import namedtuple

from . import block_registry
from .entity_overlays import native_item
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt
from .visible_item_slot_data import SOURCE_SHA256

SCHEMA_VERSION = 1
ENGINE_VERSION = '3.10.0.420447'
ContentSlot = namedtuple('ContentSlot', 'family index item direction')
SHELF_NAMES = frozenset('minecraft:'+wood+'_shelf' for wood in (
    'acacia', 'bamboo', 'birch', 'cherry', 'crimson', 'dark_oak', 'jungle',
    'mangrove', 'oak', 'pale_oak', 'spruce', 'warped'))
CAMPFIRE_NAMES = frozenset(('minecraft:campfire', 'minecraft:soul_campfire'))
SLOT_NAMES = SHELF_NAMES | CAMPFIRE_NAMES | frozenset(('minecraft:lectern',))


def _list(value):
    if isinstance(value, list):
        return value
    if isinstance(value, dict) and scalar(value, '__type__') == 9:
        result = scalar(value, '__value__')
        return result if isinstance(result, list) else None
    return None


def content_slots(material, actor, engine_version):
    if engine_version != ENGINE_VERSION or material[0] not in SLOT_NAMES:
        return None
    root = root_payload(entity_nbt(actor))
    states = block_registry.states(material)
    if root is None or states is None:
        return None
    direction = states.get('minecraft:cardinal_direction')
    if direction not in ('north', 'south', 'west', 'east'):
        return None
    identifier = scalar(root, 'id')
    if material[0] in SHELF_NAMES and identifier in ('Shelf', b'Shelf'):
        entries = _list(root.get(field_key(root, 'Items')))
        if entries is None:
            return () if field_key(root, 'Items') is None else None
        if len(entries) != 3:
            return None
        # Measured shelf order is positional; the sample has no Slot field.
        return tuple(ContentSlot('shelf', index, item, direction)
                     for index, entry in enumerate(entries)
                     for item in (native_item(root_payload(entry)),) if item is not None)
    if material[0] in CAMPFIRE_NAMES and identifier in ('Campfire', b'Campfire'):
        return tuple(ContentSlot('campfire', index, item, direction)
                     for index in range(4)
                     for item in (native_item(root_payload(root.get(field_key(root, 'Item%d' % (index+1))))),)
                     if item is not None)
    if material[0] == 'minecraft:lectern' and identifier in ('Lectern', b'Lectern'):
        item = native_item(root_payload(root.get(field_key(root, 'book'))))
        if item is None:
            return ()
        if scalar(root, 'hasBook') != 1:
            return None
        return (ContentSlot('lectern', 0, item, direction),)
    return None
