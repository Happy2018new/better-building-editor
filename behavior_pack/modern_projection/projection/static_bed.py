"""Native-textured bed halves constrained to their own logical render cells."""
from . import block_registry as registry
from .block_registry import states
from .cell import actor_data, foreground, integer_types
from .native_appearance import validate_source
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt, render_actor
from .static_bed_data import SOURCE_VERSION, PALETTE_SHA256

BED_COLORS = ('white', 'orange', 'magenta', 'light_blue', 'yellow', 'lime',
              'pink', 'gray', 'silver', 'cyan', 'purple', 'blue', 'brown',
              'green', 'red', 'black')
BED_DIRECTIONS = ((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))
BED_PROXIES = dict(((color, direction, head),
                   'modern_projection:preview_bed_' + color + '_' + str(direction) +
                   ('_head' if head else '_foot'))
                  for color in BED_COLORS for direction in range(4) for head in (False, True))


def bed_color(actor):
    root = root_payload(entity_nbt(actor))
    if root is not None and scalar(root, 'id') in ('Bed', b'Bed'):
        tag = root.get(field_key(root, 'color'))
        color = scalar(root, 'color')
        if (isinstance(tag, dict) and scalar(tag, '__type__') == 1 and
                isinstance(color, integer_types) and type(color) is not bool and 0 <= color < 16):
            return color
        return None
    renderer = root_payload(render_actor(actor))
    color = scalar(renderer, 'color') if renderer is not None else None
    return color if isinstance(color, integer_types) and type(color) is not bool and 0 <= color < 16 else None


def bed_proxy(material, actor, inferred_color=None):
    if material[0] != 'minecraft:bed':
        return None
    record = states(material)
    if record is None or type(record.get('head_piece_bit')) is not bool:
        return None
    direction = record.get('direction')
    if not isinstance(direction, integer_types) or type(direction) is bool or not 0 <= direction < 4:
        return None
    color = bed_color(actor) if inferred_color is None else inferred_color
    if color is None:
        return None
    if SOURCE_VERSION != registry.source_version() or PALETTE_SHA256 != registry.fingerprint():
        raise ValueError('Native bed models need sources for this block registry')
    validate_source()
    return (BED_PROXIES[(BED_COLORS[color], direction, record['head_piece_bit'])], 0)


def _partner(position, material):
    record = states(material)
    if record is None or record.get('head_piece_bit') is not False:
        return None
    direction = record.get('direction')
    if not isinstance(direction, integer_types) or type(direction) is bool or not 0 <= direction < 4:
        return None
    delta = BED_DIRECTIONS[direction]
    return tuple(position[axis] + delta[axis] for axis in range(3)), direction


def _head_color(material, actor, direction):
    record = states(material)
    if (material[0] != 'minecraft:bed' or record is None or
            record.get('head_piece_bit') is not True or record.get('direction') != direction):
        return None
    return bed_color(actor)


def document_bed_color(document, position, material):
    partner = _partner(position, material)
    if partner is None:
        return None
    value = document.blocks.get(partner[0])
    return _head_color(foreground(value), actor_data(value), partner[1]) if value is not None else None


def palette_bed_colors(entries, actors, volume):
    if volume is None:
        return {}
    depth, width, height = volume
    materials = dict((index, value) for value, positions in entries.items()
                     if value[0] == 'minecraft:bed' for index in positions)
    payloads = actors.get('minecraft:bed', actors.get(b'minecraft:bed', {}))
    result = {}
    for index, material in materials.items():
        position = (index // depth % width, index // (depth * width), index % depth)
        partner = _partner(position, material)
        if partner is None:
            continue
        x, y, z = partner[0]
        if not (0 <= x < width and 0 <= y < height and 0 <= z < depth):
            continue
        head_index = (y * width + x) * depth + z
        head = materials.get(head_index)
        if head is None:
            continue
        color = _head_color(head, payloads.get(head_index), partner[1])
        if color is not None:
            result[index] = color
    return result
