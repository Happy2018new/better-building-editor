# -*- coding: utf-8 -*-
"""Resolve vanilla multi-block part relationships from native block states."""
from __future__ import unicode_literals
from . import block_registry as registry

_BED_DIRECTIONS = ((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))


def from_states(name, properties):
    resolver = getattr(registry, 'from_states', None)
    if resolver is not None:
        return resolver(name, properties)
    for aux in registry.aux_values(name):
        value = (name, aux)
        if registry.states(value) == properties:
            return value
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
    if 'upper_block_bit' in properties:
        upper = properties['upper_block_bit']
        offset = (0, -1 if upper else 1, 0)
        key = 'upper_block_bit'
        paired_value = not upper
    elif properties.get('sea_grass_type') in ('double_bot', 'double_top'):
        lower = properties['sea_grass_type'] == 'double_bot'
        offset = (0, 1 if lower else -1, 0)
        key = 'sea_grass_type'
        paired_value = 'double_top' if lower else 'double_bot'
    elif 'head_piece_bit' in properties:
        head = properties['head_piece_bit']
        direction = properties.get('direction')
        if type(direction) is not int or not 0 <= direction < len(_BED_DIRECTIONS):
            raise ValueError('床方向状态无效，无法解析床头与床脚')
        sign = -1 if head else 1
        offset = tuple(sign * value for value in _BED_DIRECTIONS[direction])
        key = 'head_piece_bit'
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
    for key in ('upper_block_bit', 'sea_grass_type', 'head_piece_bit'):
        if key in original_states and key in value_states:
            value_states[key] = original_states[key]
            return from_states(value[0], value_states) or requested
    return requested


def group_is_upper(value):
    try:
        value = registry.canonical(value)
    except ValueError:
        return False
    properties = registry.states(value) or {}
    return (properties.get('upper_block_bit') is True or
            properties.get('sea_grass_type') == 'double_top' or
            properties.get('head_piece_bit') is True)


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
