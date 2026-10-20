# -*- coding: utf-8 -*-
"""Render-only shelf bodies in the common block palette.

The original document remains the owner of the three item slots.  Custom block
geometry preserves the native atlas and ordinary context clipping, but does not
reproduce the native terrain tessellator's vertical ambient-occlusion gradient.
"""
from . import block_registry

ENGINE_VERSION = '3.10.0.420447'
# Enabled after the Scene/full/missing smoke check, independently of AO parity.
BODY_ENABLED = False
WOODS = ('acacia', 'bamboo', 'birch', 'cherry', 'crimson', 'dark_oak',
         'jungle', 'mangrove', 'oak', 'pale_oak', 'spruce', 'warped')
DIRECTIONS = ('north', 'east', 'south', 'west')
FRONTS = ('unpowered', 'unconnected', 'right', 'center', 'left')
POWERED_FRONTS = ('unconnected', 'right', 'center', 'left')
SHELF_NAMES = frozenset('minecraft:' + wood + '_shelf' for wood in WOODS)


def identifier(wood, front, direction):
    return 'modern_projection:preview_shelf_' + wood + '_' + front + '_' + direction + '_body'


INTERNAL_BLOCKS = frozenset(identifier(wood, front, direction)
                            for wood in WOODS for front in FRONTS for direction in DIRECTIONS)


def accepts_item_contents(material, actor):
    """Narrow content admission; the item profile owns per-item qualification."""
    return BODY_ENABLED and material == ('minecraft:oak_shelf', 0)


def body_proxy(material, record):
    """Validate semantic states, including NBT types, before replacing a shelf."""
    if material[0] not in SHELF_NAMES:
        return None
    expected = block_registry.states(material)
    keys = ('minecraft:cardinal_direction', 'powered_bit', 'powered_shelf_type')
    if expected is None or set(expected) != set(keys):
        return None
    if record and (record != expected or type(record.get('powered_bit')) is not bool or
                   type(record.get('powered_shelf_type')) is not int):
        return None
    direction = expected.get('minecraft:cardinal_direction')
    powered, role = expected.get('powered_bit'), expected.get('powered_shelf_type')
    if (direction not in DIRECTIONS or type(powered) is not bool or
            type(role) is not int or not 0 <= role < len(POWERED_FRONTS)):
        return None
    front = POWERED_FRONTS[role] if powered else 'unpowered'
    wood = material[0][len('minecraft:'):-len('_shelf')]
    return identifier(wood, front, direction), 0


def prepare_shelves(common, records):
    """Replace body geometry without adding cells, overlays, or item ownership."""
    if not BODY_ENABLED:
        return common, records, frozenset()
    result, state_records, replaced = {}, {}, set()
    for material, positions in common.items():
        proxy = body_proxy(material, records.get(material))
        rendered = proxy if proxy is not None else material
        result.setdefault(rendered, []).extend(positions)
        if proxy is None:
            if material in records:
                state_records[material] = records[material]
        else:
            replaced.update((material[0], index) for index in positions)
    return result, state_records, frozenset(replaced)
