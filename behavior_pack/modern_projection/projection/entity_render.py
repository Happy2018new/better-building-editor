"""Versioned static render adapters for verified native palette pose failures."""
from __future__ import unicode_literals
from . import block_registry, static_chest_data, static_shulker_data
from .cell import actor_data, foreground, integer_types, freeze, thaw
from .block_registry import states
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import chest_is_single, render_actor, entity_nbt
from .static_skull import SKULL_PROXIES, skull_proxy
from .static_bed import BED_PROXIES, bed_proxy, palette_bed_colors
from .native_render_profile import coordinate_mode

SCHEMA_VERSION = 4
SHULKER_COLORS = ('undyed', 'white', 'orange', 'magenta', 'light_blue', 'yellow',
                  'lime', 'pink', 'gray', 'light_gray', 'cyan', 'purple', 'blue',
                  'brown', 'green', 'red', 'black')
SHULKER_PROXIES = dict(
    ('minecraft:' + color + '_shulker_box', tuple(
        'modern_projection:preview_shulker_' + color + '_' + str(facing)
        for facing in range(6))) for color in SHULKER_COLORS)
CHEST_DIRECTIONS = ('south', 'west', 'north', 'east')
COPPER_CHEST_STAGES = ('default', 'exposed', 'weathered', 'oxidized')
COPPER_CHEST_PROXIES = dict(
    ('minecraft:' + ('waxed_' if waxed else '') +
     ('' if stage == 'default' else stage + '_') + 'copper_chest',
     dict(((direction, part), 'modern_projection:preview_copper_chest_' +
           stage + '_' + direction + '_' + part)
          for direction in CHEST_DIRECTIONS for part in ('single', 'main', 'sub')))
    for stage in COPPER_CHEST_STAGES for waxed in (False, True))
CHEST_PROXIES = dict(COPPER_CHEST_PROXIES)
CHEST_PROXIES.update(dict(
    ('minecraft:' + name, dict(((direction, part),
        'modern_projection:preview_chest_' + stage + '_' + direction + '_' + part)
        for direction in CHEST_DIRECTIONS
        for part in (('single',) if name == 'ender_chest' else ('single', 'main', 'sub'))))
    for name, stage in (('chest', 'normal'), ('trapped_chest', 'trapped'), ('ender_chest', 'ender'))))
INTERNAL_BLOCKS = frozenset(
    [name for names in SHULKER_PROXIES.values() for name in names] +
    [name for names in CHEST_PROXIES.values() for name in names.values()] +
    [name for names in SKULL_PROXIES.values() for name in names.values()] +
    list(BED_PROXIES.values()))


def native_actor(material, actor):
    """Refresh observed render fields; saved payloads remain untouched."""
    from .native_appearance import SKULL_NAMES, angle, validate_source
    from .native_sign import native_sign_actor
    from .native_pot import native_pot_actor
    renderer = render_actor(actor)
    sign = native_sign_actor(material, actor, renderer)
    if sign is not None:
        return sign
    pot = native_pot_actor(material, renderer, actor)
    if pot is not None:
        return pot
    if material[0] == 'minecraft:bed':
        return _bed_actor(material, actor, renderer)
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


def _bed_actor(material, actor, renderer):
    from .block_registry import states
    from .native_appearance import validate_source
    root = root_payload(entity_nbt(actor))
    record = states(material)
    if record is None:
        return renderer
    if root is not None and scalar(root, 'id') in ('Bed', b'Bed'):
        tag = root.get(field_key(root, 'color'))
        color = scalar(root, 'color')
        if (not isinstance(tag, dict) or scalar(tag, '__type__') != 1 or
                not isinstance(color, integer_types) or type(color) is bool or not 0 <= color < 16):
            return renderer
        validate_source()
        result = thaw(freeze(renderer)) if renderer is not None else {}
        result.update(color=color, direction=record['direction'])
        return result
    if renderer is not None and field_key(renderer, 'direction') is not None:
        validate_source()
        result = thaw(freeze(renderer))
        from .nbt_spatial import set_scalar
        set_scalar(result, 'direction', record['direction'])
        return result
    return renderer


def _chest_part(actor):
    if chest_is_single(actor):
        return 'single'
    renderer = root_payload(render_actor(actor))
    paired = scalar(renderer, 'chestIsLargeChest') if renderer is not None else None
    if type(paired) is not bool:
        return None
    if not paired:
        return 'single'
    main = scalar(renderer, 'chestMainSubChest')
    return None if type(main) is not bool else ('main' if main else 'sub')


def chest_proxy(material, actor, inferred_part=None):
    names = CHEST_PROXIES.get(material[0])
    if names is None:
        return None
    _validate_container_source(static_chest_data)
    properties = states(material)
    direction = properties.get('minecraft:cardinal_direction') if properties else None
    if direction not in CHEST_DIRECTIONS:
        return None
    part = _chest_part(actor) or inferred_part or 'single'
    if material[0] == 'minecraft:ender_chest':
        part = 'single'
    return (names[(direction, part)], 0)


def static_proxy(material, actor, inferred_part=None, inferred_bed_color=None):
    bed = bed_proxy(material, actor, inferred_bed_color)
    if bed is not None:
        return bed
    skull = skull_proxy(material, actor)
    if skull is not None:
        return skull
    chest = chest_proxy(material, actor, inferred_part)
    if chest is not None:
        return chest
    names = SHULKER_PROXIES.get(material[0])
    if names is None:
        return None
    _validate_container_source(static_shulker_data)
    root = root_payload(entity_nbt(actor))
    facing = scalar(root, 'facing') if root is not None and scalar(root, 'id') in ('ShulkerBox', b'ShulkerBox') else None
    if not isinstance(facing, integer_types) or type(facing) is bool or not 0 <= facing <= 5:
        renderer = root_payload(render_actor(actor))
        facing = scalar(renderer, 'facingDirection') if renderer is not None else None
    if not isinstance(facing, integer_types) or type(facing) is bool or not 0 <= facing <= 5:
        facing = 1
    return (names[facing], 0)


def _validate_container_source(source):
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != block_registry.source_version()
            or source.PALETTE_SHA256.lower() != block_registry.fingerprint().lower()):
        raise ValueError('Static container models need regeneration for this block registry')


def _adjacent_chest_parts(value, positions, volume, payloads):
    if volume is None or value[0] == 'minecraft:ender_chest':
        return {}
    properties = states(value)
    direction = properties.get('minecraft:cardinal_direction') if properties else None
    if direction not in CHEST_DIRECTIONS:
        return {}
    depth, width = volume[:2]
    delta = {'north': depth, 'south': -depth, 'east': 1, 'west': -1}[direction]
    available = set(index for index in positions if _chest_part(payloads.get(index)) != 'single')
    result = {}
    for index in positions:
        if index not in available:
            continue
        x, z = index // depth % width, index % depth
        neighbors = []
        for offset, main in ((delta, True), (-delta, False)):
            candidate = index + offset
            if candidate not in available or candidate < 0:
                continue
            cx, cz = candidate // depth % width, candidate % depth
            if index // (width * depth) == candidate // (width * depth) and abs(x - cx) + abs(z - cz) == 1:
                neighbors.append((candidate, main))
        if len(neighbors) == 1:
            result[index] = 'main' if neighbors[0][1] else 'sub'
    # Only mutual single-neighbor pairs may form a large chest.
    return dict((index, part) for index, part in result.items()
                if result.get(index + (delta if part == 'main' else -delta)) ==
                ('sub' if part == 'main' else 'main'))


def document_chest_part(document, position, material):
    """Infer a missing client pair pose using the complete logical snapshot."""
    if material[0] not in CHEST_PROXIES or material[0] == 'minecraft:ender_chest':
        return None
    properties = states(material)
    direction = properties.get('minecraft:cardinal_direction') if properties else None
    delta = {'north': (1, 0, 0), 'south': (-1, 0, 0),
             'east': (0, 0, 1), 'west': (0, 0, -1)}.get(direction)
    if delta is None:
        return None

    def neighbors(pos):
        result = []
        for sign in (1, -1):
            candidate = tuple(pos[axis] + sign * delta[axis] for axis in range(3))
            value = document.blocks.get(candidate)
            if (value is not None and foreground(value) == material and
                    _chest_part(actor_data(value)) != 'single'):
                result.append((candidate, sign))
        return result

    adjacent = neighbors(position)
    if len(adjacent) != 1 or len(neighbors(adjacent[0][0])) != 1:
        return None
    return 'main' if adjacent[0][1] == 1 else 'sub'


def prepare_static_entities(entries, actors, volume=None, inferred_chest_parts=None,
                            inferred_bed_colors=None, native_render_profile=None):
    """Replace only render cells; return actor slots consumed by static meshes."""
    result, replaced = {}, set()
    bed_colors = palette_bed_colors(entries, actors, volume)
    for value, positions in entries.items():
        if (value[0] not in SHULKER_PROXIES and value[0] not in CHEST_PROXIES and
                value[0] not in SKULL_PROXIES and value[0] != 'minecraft:bed'):
            result.setdefault(value, []).extend(positions)
            continue
        payloads = actors.get(value[0], actors.get(value[0].encode('utf8'), {}))
        parts = _adjacent_chest_parts(value, positions, volume, payloads) if value[0] in CHEST_PROXIES else {}
        for index in positions:
            if coordinate_mode(native_render_profile, value, payloads.get(index)) is not None:
                result.setdefault(value, []).append(index)
                continue
            inferred = (inferred_chest_parts or {}).get((value[0], index), parts.get(index))
            color = (inferred_bed_colors or {}).get(index, bed_colors.get(index))
            proxy = static_proxy(value, payloads.get(index), inferred, color)
            if proxy is None:
                result.setdefault(value, []).append(index)
                continue
            result.setdefault(proxy, []).append(index)
            replaced.add((value[0], index))
    return result, replaced
