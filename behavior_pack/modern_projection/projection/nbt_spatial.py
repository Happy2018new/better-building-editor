# -*- coding: utf-8 -*-
"""Transform known block-entity spatial fields while preserving NBT tags.

Inventories, item tags, commands and arbitrary nested coordinates are data, not
positions of this block entity. They must never be rewritten recursively.
"""
from .cell import freeze, thaw, integer_types, text_type

SCHEMA_VERSION = 1
OPERATIONS = frozenset(('rotate_y90', 'rotate_y180', 'rotate_y270',
                        'mirror_x', 'mirror_y', 'mirror_z'))
VISIBLE_DIRECTIONS = (('facingDirection', 'facing_direction', 6),
                      ('signStandingRotation', 'ground_sign_direction', 16))
# Actor-only directions require an entity ID; arbitrary fields are opaque data.
NBT_DIRECTIONS = {'ShulkerBox': (('facing', 'facing_direction', 6),)}
NBT_DIRECTIONS.update((name.encode('ascii'), rules)
                      for name, rules in tuple(NBT_DIRECTIONS.items()))


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
    result = thaw(freeze(data))
    _rebase_actor(result, delta)
    return result


def _rebase_actor(data, delta):
    if data is None:
        return
    from .visible_actor import is_envelope
    if is_envelope(data):
        _rebase_actor(data['render'], delta)
        _rebase_actor(data['nbt'], delta)
        return
    root = root_payload(data)
    if root is None:
        raise ValueError('Block entity payload must be a compound')
    for name, axis in (('x', 0), ('y', 1), ('z', 2), ('pairx', 0), ('pairz', 2)):
        value = scalar(root, name)
        if isinstance(value, integer_types) and type(value) is not bool:
            set_scalar(root, name, value + delta[axis])


def transform_pair(data, origin, operation):
    """Transform visible actor directions and pair offsets before moving the cell."""
    if operation not in OPERATIONS or data is None:
        return data
    result = thaw(freeze(data))
    _transform_actor(result, origin, operation)
    return result


def _transform_actor(data, origin, operation):
    if data is None:
        return
    from .visible_actor import is_envelope
    if is_envelope(data):
        _transform_actor(data['render'], origin, operation)
        _transform_actor(data['nbt'], origin, operation)
        return
    root = root_payload(data)
    if root is None:
        raise ValueError('Block entity payload must be a compound')
    _directions(root, operation)
    _chest_roles(root, operation)
    _pair_coordinates(root, origin, operation)


def _directions(root, operation):
    from .state_transform import transform_states
    identifier = scalar(root, 'id')
    rules = NBT_DIRECTIONS.get(identifier, ()) if isinstance(identifier, (bytes, text_type)) else ()
    for field, property_name, maximum in VISIBLE_DIRECTIONS + rules:
        value = scalar(root, field)
        if isinstance(value, integer_types) and type(value) is not bool and 0 <= value < maximum:
            set_scalar(root, field, transform_states({property_name: value}, operation)[property_name])


def _chest_roles(root, operation):
    if operation not in ('mirror_x', 'mirror_z'):
        return
    if scalar(root, 'chestIsLargeChest') is True:
        main = scalar(root, 'chestMainSubChest')
        if type(main) is bool:
            set_scalar(root, 'chestMainSubChest', not main)
            set_scalar(root, 'chestModelOffset', 0.0 if not main else -0.5)
    identifier = scalar(root, 'id')
    if identifier not in ('Chest', b'Chest'):
        return
    pair = (scalar(root, 'pairx'), scalar(root, 'pairz'))
    if any(not isinstance(value, integer_types) or type(value) is bool for value in pair):
        return
    for field in ('pairlead', 'renderlead'):
        lead = scalar(root, field)
        if type(lead) is bool:
            set_scalar(root, field, not lead)
        elif isinstance(lead, integer_types) and lead in (0, 1):
            set_scalar(root, field, 1 - lead)


def _pair_coordinates(root, origin, operation):
    if operation == 'mirror_y':
        return
    pair_x, pair_z = scalar(root, 'pairx'), scalar(root, 'pairz')
    if (not isinstance(pair_x, integer_types) or type(pair_x) is bool or
            not isinstance(pair_z, integer_types) or type(pair_z) is bool):
        return
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
