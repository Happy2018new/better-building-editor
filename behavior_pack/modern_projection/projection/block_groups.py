# -*- coding: utf-8 -*-
"""Resolve vanilla multi-block part relationships from native block states."""
from __future__ import unicode_literals
from . import block_registry as registry
from .cell import actor_data, background, foreground, integer_types, layer, make_cell
from .nbt_spatial import field_key, root_payload, scalar, set_scalar
from .visible_actor import compose_actor, entity_nbt, render_actor

_BED_DIRECTIONS = ((0, 0, 1), (-1, 0, 0), (0, 0, -1), (1, 0, 0))
_NON_PAIRED_UPPER_BLOCKS = frozenset(('minecraft:pale_moss_carpet',))
_MIN_GROUP_GROWTH = {'minecraft:pitcher_crop': 3}
_CHESTS = frozenset(name for name in registry.BLOCKS
                    if name.startswith('minecraft:') and
                    (name == 'minecraft:chest' or name.endswith('_chest')) and
                    name != 'minecraft:ender_chest')
_CHEST_PARTNER = {'north': (1, 0, 0), 'east': (0, 0, 1),
                  'south': (-1, 0, 0), 'west': (0, 0, -1)}
_CHEST_FACING = {'north': 2, 'south': 3, 'west': 4, 'east': 5}


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
    if properties.get('growth', 0) < _MIN_GROUP_GROWTH.get(name, 0):
        return None
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
    if foreground(value)[0] not in _CHESTS:
        return None
    data = actor_data(value)
    actor = root_payload(entity_nbt(data) or data)
    if actor is None:
        return None
    pair_x, pair_z = scalar(actor, 'pairx'), scalar(actor, 'pairz')
    if (not isinstance(pair_x, integer_types) or type(pair_x) is bool or
            not isinstance(pair_z, integer_types) or type(pair_z) is bool):
        return None
    partner = (pair_x, pos[1], pair_z)
    return None if partner == pos else partner


def _chest_direction(value):
    native = registry.try_canonical(foreground(value))
    properties = (registry.states(native) or {}) if native is not None else {}
    return properties.get('minecraft:cardinal_direction')


def chest_render_pair_position(value, pos):
    """Resolve the native client chest renderer's main/sub half relationship."""
    if foreground(value)[0] not in _CHESTS:
        return None
    data = actor_data(value)
    actor = root_payload(render_actor(data) or entity_nbt(data))
    if actor is None or scalar(actor, 'chestIsLargeChest') is not True:
        return None
    main = scalar(actor, 'chestMainSubChest')
    offset = _CHEST_PARTNER.get(_chest_direction(value))
    if type(main) is not bool or offset is None:
        return None
    sign = 1 if main else -1
    return tuple(pos[i] + sign * offset[i] for i in range(3))


def _single_chest(value):
    root = root_payload(render_actor(actor_data(value)))
    return root is not None and scalar(root, 'chestIsLargeChest') is False


def _chest_candidates(get_cell, value, pos, respect_single=False):
    name = foreground(value)[0]
    if name not in _CHESTS or (respect_single and _single_chest(value)):
        return []
    direction = _chest_direction(value)
    if direction not in ('north', 'south', 'east', 'west'):
        return []
    offsets = ((1, 0, 0), (-1, 0, 0)) if direction in ('north', 'south') else (
        (0, 0, 1), (0, 0, -1))
    candidates = []
    for offset in offsets:
        target = tuple(pos[i] + offset[i] for i in range(3))
        other = get_cell(target)
        if (other is not None and foreground(other)[0] == name and
                _chest_direction(other) == direction and
                (not respect_single or not _single_chest(other))):
            linked = actor_pair_position(other, target) or chest_render_pair_position(other, target)
            if linked is None or linked == pos:
                candidates.append(target)
    return candidates


def _adjacent_chest_position(get_cell, value, pos, respect_single=False):
    candidates = _chest_candidates(get_cell, value, pos, respect_single)
    if len(candidates) != 1:
        return None
    partner = candidates[0]
    other = get_cell(partner)
    linked = actor_pair_position(other, partner) or chest_render_pair_position(other, partner)
    if linked == pos or _chest_candidates(get_cell, other, partner, respect_single) == [pos]:
        return partner
    return None


def chest_pair_actor(value, pos, partner=None):
    """Set client-visible chest render fields, preserving unrelated actor data."""
    if foreground(value)[0] not in _CHESTS:
        return value
    direction = _chest_direction(value)
    if direction not in _CHEST_PARTNER:
        return value
    data = actor_data(value)
    nbt = entity_nbt(data)
    render = render_actor(data)
    render = {} if render is None else render
    root = root_payload(render)
    if root is None:
        return value
    main_partner = tuple(pos[i] + _CHEST_PARTNER[direction][i] for i in range(3))
    main = partner is None or partner == main_partner
    fields = {'chestIsLargeChest': partner is not None,
              'chestMainSubChest': main, 'chestModelOffset': 0.0 if main else -0.5,
              'facingDirection': _CHEST_FACING[direction]}
    for name, new in fields.items():
        if not set_scalar(root, name, new):
            root[name] = new
    for name, default in (('chestIsGlobalChest', False), ('chestOpenness', 0.0),
                          ('chestOldOpenness', 0.0)):
        if field_key(root, name) is None:
            root[name] = default
    for pair_root in (root, root_payload(nbt)):
        if pair_root is None:
            continue
        for name, axis in (('pairx', 0), ('pairz', 2)):
            key = field_key(pair_root, name)
            if key is None:
                continue
            if partner is None:
                del pair_root[key]
            else:
                set_scalar(pair_root, name, partner[axis])
    return make_cell(foreground(value), background(value), compose_actor(render, nbt))


def hydrate_chest_actor(value, pos):
    """Fill missing client chest geometry fields from captured pairing NBT."""
    if foreground(value)[0] not in _CHESTS:
        return value
    root = root_payload(render_actor(actor_data(value)))
    if root is not None and field_key(root, 'chestIsLargeChest') is not None:
        return value
    return chest_pair_actor(value, pos, actor_pair_position(value, pos))


def paired_cell_position(get_cell, pos, index=None):
    """Resolve a paired block from either block states or actor coordinates."""
    value = get_cell(pos)
    if value is None:
        return None
    if index == 2:
        index = 0 if foreground(value) != ('minecraft:air', 0) else 1
    if index is None:
        index = 0 if group_partner(foreground(value)) is not None or foreground(value)[0] in _CHESTS else 1
    front = layer(value, index)
    if group_partner(front) is not None:
        return paired_cell_part(get_cell, pos, index)[0]
    if index or front[0] not in _CHESTS:
        return None
    partner_pos = actor_pair_position(value, pos) or chest_render_pair_position(value, pos)
    if partner_pos is None:
        return _adjacent_chest_position(get_cell, value, pos, respect_single=True)
    partner = get_cell(partner_pos)
    if (partner is None or foreground(partner)[0] != front[0] or
            _chest_direction(partner) != _chest_direction(value)):
        raise ValueError('双箱缺少相同种类的对应箱子')
    direction = _chest_direction(value)
    offset = tuple(partner_pos[i] - pos[i] for i in range(3))
    if (sum(abs(v) for v in offset) != 1 or offset[1] or
            (direction in ('north', 'south') and offset[2]) or
            (direction in ('east', 'west') and offset[0])):
        raise ValueError('双箱对应箱子必须紧邻其侧面')
    reciprocal = actor_pair_position(partner, partner_pos) or chest_render_pair_position(partner, partner_pos)
    if reciprocal is not None and reciprocal != pos:
        raise ValueError('双箱方块实体的配对坐标不一致')
    return partner_pos


def paired_cell_part(get_cell, pos, index=0):
    """Return the partner position and its actual layer, including snowy parts."""
    value = get_cell(pos)
    if value is None:
        return None
    if index == 2:
        index = 0 if foreground(value) != ('minecraft:air', 0) else 1
    relationship = group_partner(layer(value, index))
    if relationship is None:
        partner = paired_cell_position(get_cell, pos, index)
        return (partner, 0) if partner is not None else None
    offset, expected = relationship
    partner = tuple(pos[i] + offset[i] for i in range(3))
    other = get_cell(partner)
    if other is not None:
        for selected in (index, 1 - index):
            if registry.try_canonical(layer(other, selected)) == expected:
                return partner, selected
    raise ValueError('多格方块缺少对应部件或状态不匹配：%s' % layer(value, index)[0])


def paired_cell_positions(get_cell, pos, index=None):
    indices = (0, 1) if index is None else (index,)
    return tuple(set(partner for selected in indices
                     for partner in (paired_cell_position(get_cell, pos, selected),)
                     if partner is not None))


def has_group_link(value, pos, get_cell=None, index=None):
    if index == 2:
        index = 0 if foreground(value) != ('minecraft:air', 0) else 1
    indices = (0, 1) if index is None else (index,)
    if any(group_partner(layer(value, selected)) is not None for selected in indices):
        return True
    if index == 1:
        return False
    return (
            actor_pair_position(value, pos) is not None or
            chest_render_pair_position(value, pos) is not None or
            (get_cell is not None and _adjacent_chest_position(get_cell, value, pos, respect_single=True) is not None))
