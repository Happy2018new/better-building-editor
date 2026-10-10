"""Versioned static render adapters for verified native palette pose failures."""
from __future__ import unicode_literals
from .cell import integer_types, freeze, thaw
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import render_actor, entity_nbt

SCHEMA_VERSION = 2
SHULKER_COLORS = ('undyed', 'white', 'orange', 'magenta', 'light_blue', 'yellow',
                  'lime', 'pink', 'gray', 'light_gray', 'cyan', 'purple', 'blue',
                  'brown', 'green', 'red', 'black')
SHULKER_PROXIES = dict(
    ('minecraft:' + color + '_shulker_box', tuple(
        'modern_projection:preview_shulker_' + color + '_' + str(facing)
        for facing in range(6))) for color in SHULKER_COLORS)
INTERNAL_BLOCKS = frozenset(name for names in SHULKER_PROXIES.values() for name in names)


def native_actor(material, actor):
    """Supply only observed Skull fields; saved payloads remain untouched."""
    from .native_appearance import SKULL_NAMES, angle, validate_source
    renderer = render_actor(actor)
    if material[0] not in SKULL_NAMES:
        return renderer
    root = root_payload(entity_nbt(actor))
    if root is None or scalar(root, 'id') not in ('Skull', b'Skull'):
        return renderer
    from .block_registry import states
    record = states(material)
    rotation = scalar(root, 'Rotation')
    skull_type = scalar(root, 'SkullType')
    rotation_tag = root.get(field_key(root, 'Rotation'))
    type_tag = root.get(field_key(root, 'SkullType'))
    if (not isinstance(rotation_tag, dict) or scalar(rotation_tag, '__type__') != 5
            or not isinstance(type_tag, dict) or scalar(type_tag, '__type__') != 1
            or record is None or not angle(rotation) or not isinstance(skull_type, integer_types)
            or type(skull_type) is bool or not 0 <= skull_type <= 255):
        return renderer
    validate_source()
    result = thaw(freeze(renderer)) if renderer is not None else {'progress': 0.0}
    result.update(facingDirection=record['facing_direction'], rotation=rotation,
                  skullType=skull_type)
    return result


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
