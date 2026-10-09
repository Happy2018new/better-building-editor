# -*- coding: utf-8 -*-
"""Translate only documented block-entity root coordinates, preserving NBT tags.

Inventories, item tags, commands and arbitrary nested coordinates are data, not
positions of this block entity. They must never be rewritten recursively.
"""
from .cell import freeze, thaw, integer_types


def root_payload(data):
    """Return a mutable root compound view, with or without an SDK root tag."""
    if not isinstance(data, dict):
        return None
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
    """Clone a block actor and translate root x/y/z and chest pairx/pairz."""
    if data is None:
        return None
    result = thaw(freeze(data))
    root = root_payload(result)
    if root is None:
        raise ValueError('Block entity payload must be a compound')
    for name, axis in (('x', 0), ('y', 1), ('z', 2), ('pairx', 0), ('pairz', 2)):
        value = scalar(root, name)
        if isinstance(value, integer_types) and type(value) is not bool:
            set_scalar(root, name, value + delta[axis])
    return result
