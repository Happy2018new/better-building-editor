"""Versioned static render adapters for verified native palette pose failures."""
from __future__ import unicode_literals
from .cell import integer_types
from .nbt_spatial import root_payload, scalar
from .visible_actor import render_actor, entity_nbt

SCHEMA_VERSION = 1
SHULKER_COLORS = ('undyed', 'white', 'orange', 'magenta', 'light_blue', 'yellow',
                  'lime', 'pink', 'gray', 'light_gray', 'cyan', 'purple', 'blue',
                  'brown', 'green', 'red', 'black')
SHULKER_PROXIES = dict(
    ('minecraft:' + color + '_shulker_box', tuple(
        'modern_projection:preview_shulker_' + color + '_' + str(facing)
        for facing in range(6))) for color in SHULKER_COLORS)
INTERNAL_BLOCKS = frozenset(name for names in SHULKER_PROXIES.values() for name in names)


def static_proxy(material, actor):
    names = SHULKER_PROXIES.get(material[0])
    if names is None:
        return None
    root = root_payload(entity_nbt(actor))
    facing = scalar(root, 'facing') if root is not None and scalar(root, 'id') in ('ShulkerBox', b'ShulkerBox') else None
    if not isinstance(facing, integer_types) or type(facing) is bool or not 0 <= facing <= 5:
        renderer = root_payload(render_actor(actor))
        facing = scalar(renderer, 'facingDirection') if renderer is not None else None
    if not isinstance(facing, integer_types) or type(facing) is bool or not 0 <= facing <= 5:
        facing = 1
    return (names[facing], 0)


def prepare_static_entities(entries, actors):
    """Replace only render cells; return actor slots consumed by static meshes."""
    result, replaced = {}, set()
    for value, positions in entries.items():
        if value[0] not in SHULKER_PROXIES:
            result.setdefault(value, []).extend(positions)
            continue
        payloads = actors.get(value[0], actors.get(value[0].encode('utf8'), {}))
        for index in positions:
            proxy = static_proxy(value, payloads.get(index))
            result.setdefault(proxy, []).append(index)
            replaced.add((value[0], index))
    return result, replaced
