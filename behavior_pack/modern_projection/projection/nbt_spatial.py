# -*- coding: utf-8 -*-
"""Translate documented block-entity coordinates while preserving NBT tags.

Inventories, item tags, commands and arbitrary nested coordinates are data, not
positions of this block entity. They must never be rewritten recursively.
"""
from .cell import freeze, thaw, integer_types


def root_payload(data):
    """Return a mutable root compound view, with or without an SDK root tag."""
    if not isinstance(data, dict):
        return None
    from .visible_actor import is_envelope
    if is_envelope(data):
        return root_payload(data['nbt'] if data['nbt'] is not None else data['render'])
    tagged = data.get('__value__', data.get(b'__value__'))
    return tagged if isinstance(tagged, dict) else data


def field_key(data, name):
    if name in data:
        return name
    encoded = name.encode('utf8')
    return encoded if encoded in data else None


def scalar(data, name):
    key = field_key(data, name)
    value = data.get(key) if key is not None else None
    if isinstance(value, dict):
        tag = field_key(value, '__value__')
        return value.get(tag) if tag is not None else None
    return value


def set_scalar(data, name, value):
    """Replace an existing scalar without changing its native tag or key type."""
    key = field_key(data, name)
    if key is None:
        return False
    current = data[key]
    if isinstance(current, dict):
        tag = field_key(current, '__value__')
        if tag is None:
            return False
        current[tag] = value
    else:
        data[key] = value
    return True


def rebase(data, delta):
    """Clone an actor and translate root position and chest-pair coordinates."""
    if data is None:
        return None
    from .visible_actor import is_envelope, compose_actor
    if is_envelope(data):
        return compose_actor(rebase(data['render'], delta), rebase(data['nbt'], delta))
    result = thaw(freeze(data))
    root = root_payload(result)
    if root is None:
        raise ValueError('Block entity payload must be a compound')
    for name, axis in (('x', 0), ('y', 1), ('z', 2), ('pairx', 0), ('pairz', 2)):
        value = scalar(root, name)
        if isinstance(value, integer_types) and type(value) is not bool:
            set_scalar(root, name, value + delta[axis])
    return result


def transform_pair(data, origin, operation):
    """Transform visible actor directions and pair offsets before moving the cell."""
    if operation not in ('rotate_y90', 'rotate_y180', 'rotate_y270',
                         'mirror_x', 'mirror_y', 'mirror_z') or data is None:
        return data
    from .visible_actor import is_envelope, compose_actor
    if is_envelope(data):
        return compose_actor(transform_pair(data['render'], origin, operation),
                             transform_pair(data['nbt'], origin, operation))
    result = thaw(freeze(data))
    root = root_payload(result)
    if root is None:
        raise ValueError('Block entity payload must be a compound')
    from .state_transform import transform_states
    for field, property_name, maximum in (
            ('facingDirection', 'facing_direction', 6),
            ('signStandingRotation', 'ground_sign_direction', 16)):
        value = scalar(root, field)
        if isinstance(value, integer_types) and type(value) is not bool and 0 <= value < maximum:
            set_scalar(root, field, transform_states({property_name: value}, operation)[property_name])
    if operation in ('mirror_x', 'mirror_z') and scalar(root, 'chestIsLargeChest') is True:
        main = scalar(root, 'chestMainSubChest')
        if type(main) is bool:
            set_scalar(root, 'chestMainSubChest', not main)
            set_scalar(root, 'chestModelOffset', 0.0 if not main else -0.5)
    if operation == 'mirror_y':
        return result
    pair_x, pair_z = scalar(root, 'pairx'), scalar(root, 'pairz')
    if (not isinstance(pair_x, integer_types) or type(pair_x) is bool or
            not isinstance(pair_z, integer_types) or type(pair_z) is bool):
        return result
    dx, dz = pair_x - origin[0], pair_z - origin[2]
    if operation.startswith('rotate_y'):
        for unused in range(int(operation[8:]) // 90):
            dx, dz = -dz, dx
    elif operation == 'mirror_x':
        dx = -dx
    else:
        dz = -dz
    set_scalar(root, 'pairx', origin[0] + dx)
    set_scalar(root, 'pairz', origin[2] + dz)
    return result
