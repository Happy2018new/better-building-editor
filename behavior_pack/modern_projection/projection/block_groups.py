# -*- coding: utf-8 -*-
"""Resolve vanilla multi-block part relationships from native block states."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import actor_data, foreground, integer_types
from .nbt_spatial import scalar

_BED_DIRECTIONS = ((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))
_NON_PAIRED_UPPER_BLOCKS = frozenset(('minecraft:pale_moss_carpet',))


def from_states(name, properties):
    resolver = getattr(registry, 'from_states', None)
    if resolver is not None:
        return resolver(name, properties)
    for aux in registry.aux_values(name):
        value = (name, aux)
        if registry.states(value) == properties:
            return value
    return None


def _part_key(name, properties):
    if 'upper_block_bit' in properties and name not in _NON_PAIRED_UPPER_BLOCKS:
        return 'upper_block_bit'
    if properties.get('sea_grass_type') in ('double_bot', 'double_top'):
        return 'sea_grass_type'
    if 'head_piece_bit' in properties:
        return 'head_piece_bit'
    return None


def group_partner(value):
    """Return ``(offset, value)`` for the reciprocal half, or None if ungrouped."""
    try:
        value = registry.canonical(value)
    except ValueError:
        return None
    properties = registry.states(value)
    if properties is None:
        return None
    key = _part_key(value[0], properties)
    if key == 'upper_block_bit':
        upper = properties['upper_block_bit']
        offset = (0, -1 if upper else 1, 0)
        paired_value = not upper
    elif key == 'sea_grass_type':
        lower = properties['sea_grass_type'] == 'double_bot'
        offset = (0, 1 if lower else -1, 0)
        paired_value = 'double_top' if lower else 'double_bot'
    elif key == 'head_piece_bit':
        head = properties['head_piece_bit']
        direction = properties.get('direction')
        if type(direction) is not int or not 0 <= direction < len(_BED_DIRECTIONS):
            raise ValueError('床方向状态无效，无法解析床头与床脚')
        sign = -1 if head else 1
        offset = tuple(sign * value for value in _BED_DIRECTIONS[direction])
        paired_value = not head
    else:
        return None
    paired = dict(properties)
    paired[key] = paired_value
    partner = from_states(value[0], paired)
    if partner is None:
        raise ValueError('原版方块表缺少多格方块的对应部件：%s' % value[0])
    return offset, partner


def preserve_group_part(value, original):
    """Keep the selected half when replacing one paired block with another."""
    requested = value
    try:
        original = registry.canonical(original)
        value = registry.canonical(value)
    except ValueError:
        return requested
    original_states = registry.states(original)
    value_states = registry.states(value)
    if original_states is None or value_states is None:
        return value
    original_key = _part_key(original[0], original_states)
    value_key = _part_key(value[0], value_states)
    if original_key is not None and original_key == value_key:
        value_states[value_key] = original_states[original_key]
        return from_states(value[0], value_states) or requested
    return requested


def group_is_upper(value):
    try:
        value = registry.canonical(value)
    except ValueError:
        return False
    properties = registry.states(value) or {}
    key = _part_key(value[0], properties)
    if key == 'upper_block_bit':
        return properties[key] is True
    if key == 'sea_grass_type':
        return properties[key] == 'double_top'
    if key == 'head_piece_bit':
        return properties[key] is True
    return False


def expand_group_changes(changes, can_change):
    """Complete paired placements and drop incomplete placements atomically."""
    result = dict(changes)
    handled = set()
    for pos, value in tuple(changes.items()):
        if pos in handled:
            continue
        relationship = group_partner(value)
        if relationship is None:
            continue
        offset, reciprocal = relationship
        if group_is_upper(value):
            anchor = tuple(pos[i] + offset[i] for i in range(3))
            partner = pos
            anchor_value, partner_value = reciprocal, value
        else:
            anchor = pos
            partner = tuple(pos[i] + offset[i] for i in range(3))
            anchor_value, partner_value = value, reciprocal
        if (anchor not in result or partner not in result or
                not can_change(anchor) or not can_change(partner)):
            result.pop(pos, None)
            continue
        result[anchor], result[partner] = anchor_value, partner_value
        handled.add(anchor)
        handled.add(partner)
    return result


def paired_position(get_block, pos):
    """Validate and return the reciprocal part position for ``get_block(pos)``.

    ``get_block`` returns a native ``(name, aux)`` pair, or None when the
    requested position is outside the document. Raises when a required part
    is missing or has an incompatible state.
    """
    value = get_block(pos)
    if value is None:
        return None
    relationship = group_partner(value)
    if relationship is None:
        return None
    offset, expected = relationship
    partner_pos = tuple(pos[i] + offset[i] for i in range(3))
    actual = get_block(partner_pos)
    if actual is None:
        raise ValueError('多格方块缺少对应部件：%s' % value[0])
    try:
        actual = registry.canonical(actual)
    except ValueError:
        raise ValueError('多格方块对应部件状态不匹配：%s' % value[0])
    if actual != expected:
        raise ValueError('多格方块对应部件状态不匹配：%s' % value[0])
    return partner_pos


def actor_pair_position(value, pos):
    """Return a chest actor's linked half using its local pair coordinates."""
    if foreground(value)[0] not in ('minecraft:chest', 'minecraft:trapped_chest'):
        return None
    actor = actor_data(value)
    if actor is None:
        return None
    pair_x, pair_z = scalar(actor, 'pairx'), scalar(actor, 'pairz')
    if (not isinstance(pair_x, integer_types) or type(pair_x) is bool or
            not isinstance(pair_z, integer_types) or type(pair_z) is bool):
        return None
    partner = (pair_x, pos[1], pair_z)
    return None if partner == pos else partner


def _chest_direction(value):
    properties = registry.states(foreground(value)) or {}
    return properties.get('minecraft:cardinal_direction')


def _adjacent_chest_position(get_cell, value, pos):
    name = foreground(value)[0]
    direction = _chest_direction(value)
    if direction not in ('north', 'south', 'east', 'west'):
        return None
    offsets = ((1, 0, 0), (-1, 0, 0)) if direction in ('north', 'south') else (
        (0, 0, 1), (0, 0, -1))
    candidates = []
    for offset in offsets:
        target = tuple(pos[i] + offset[i] for i in range(3))
        other = get_cell(target)
        if (other is not None and foreground(other)[0] == name and
                _chest_direction(other) == direction):
            candidates.append(target)
    return candidates[0] if len(candidates) == 1 else None


def paired_cell_position(get_cell, pos):
    """Resolve a paired block from either block states or actor coordinates."""
    value = get_cell(pos)
    if value is None:
        return None
    front = foreground(value)
    if group_partner(front) is not None:
        def get_block(target):
            cell = get_cell(target)
            return foreground(cell) if cell is not None else None
        return paired_position(get_block, pos)
    partner_pos = actor_pair_position(value, pos)
    if partner_pos is None:
        return _adjacent_chest_position(get_cell, value, pos)
    partner = get_cell(partner_pos)
    if (partner is None or foreground(partner)[0] != front[0] or
            _chest_direction(partner) != _chest_direction(value)):
        raise ValueError('双箱缺少相同种类的对应箱子')
    reciprocal = actor_pair_position(partner, partner_pos)
    if reciprocal is not None and reciprocal != pos:
        raise ValueError('双箱方块实体的配对坐标不一致')
    return partner_pos


def has_group_link(value, pos, get_cell=None):
    return (group_partner(foreground(value)) is not None or
            actor_pair_position(value, pos) is not None or
            (get_cell is not None and _adjacent_chest_position(get_cell, value, pos) is not None))
