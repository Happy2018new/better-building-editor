"""Versioned flat item frame overlays; unknown content stays in document NBT."""
from __future__ import unicode_literals
from . import block_registry as registry
from . import static_frame_item_data as source
from .block_registry import states
from .entity_overlays import frame_item
from .native_appearance import angle
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

INTERNAL_FRAME_ITEMS = frozenset(name for profile in source.FRAME_ITEMS.values()
                                for name in profile['proxies'].values())


def frame_item_proxy(material, actor):
    item = frame_item(material, actor)
    if item is None or item['isEnchanted'] or item['userData']:
        return None
    name = item['newItemName']
    if isinstance(name, bytes):
        name = name.decode('utf8')
    profile = source.FRAME_ITEMS.get((name, item['newAuxValue']))
    if profile is None or not profile['accepted']:
        return None
    root = root_payload(entity_nbt(actor))
    tag = root.get(field_key(root, 'ItemRotation'))
    rotation = scalar(root, 'ItemRotation')
    if not isinstance(tag, dict) or scalar(tag, '__type__') != 5 or not angle(rotation):
        return None
    step = rotation % 360. / 45.
    rounded = int(round(step))
    if abs(step - rounded) > .00001:
        return None
    record = states(material)
    facing = record.get('facing_direction') if record is not None else None
    proxy = profile['proxies'].get((facing, rounded % 8))
    if proxy is None:
        return None
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Flat frame item proxies need regeneration for this block registry')
    return (proxy, 0)
