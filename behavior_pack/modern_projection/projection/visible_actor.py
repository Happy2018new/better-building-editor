"""Versioned adapters for observed client palette rendering fields."""
from __future__ import unicode_literals
from .cell import integer_types
from .nbt_spatial import field_key, root_payload, scalar

SCHEMA_VERSION = 1
ENVELOPE_KEY = '__modern_projection_actor__'


def is_envelope(data):
    return (isinstance(data, dict) and type(data.get(ENVELOPE_KEY)) is int and
            data.get(ENVELOPE_KEY) == SCHEMA_VERSION and
            'render' in data and 'nbt' in data)


def compose_actor(render, nbt):
    if nbt is None:
        return render
    return {ENVELOPE_KEY: SCHEMA_VERSION, 'render': render, 'nbt': nbt}


def render_actor(data):
    if is_envelope(data):
        return data['render']
    if isinstance(data, dict) and ENVELOPE_KEY in data:
        return None
    return None if is_tagged_nbt(data) else data


def entity_nbt(data):
    if is_envelope(data):
        return data['nbt']
    return data if is_tagged_nbt(data) else None


def chest_is_single(data):
    """Respect explicit client pose or a captured unpaired Chest NBT record."""
    renderer = root_payload(render_actor(data))
    if renderer is not None and field_key(renderer, 'chestIsLargeChest') is not None:
        return scalar(renderer, 'chestIsLargeChest') is False
    actor = root_payload(entity_nbt(data))
    return (actor is not None and scalar(actor, 'id') in ('Chest', b'Chest') and
            field_key(actor, 'pairx') is None and field_key(actor, 'pairz') is None)


def is_tagged_nbt(data):
    if not isinstance(data, dict) or not data:
        return False
    if field_key(data, '__type__') is not None and field_key(data, '__value__') is not None:
        return isinstance(root_payload(data), dict)
    identity = data.get(field_key(data, 'id'))
    if (isinstance(identity, dict) and scalar(identity, '__type__') == 8 and
            isinstance(scalar(identity, '__value__'), (bytes, type('')))):
        return True
    return all(isinstance(value, dict) and field_key(value, '__type__') is not None
               and field_key(value, '__value__') is not None for value in data.values())


def sign_sides(data):
    """Return known visible sign fields without assuming they are server NBT."""
    root = root_payload(render_actor(data))
    if root is None:
        return ()
    sides = []
    for side, suffix in ((0, ''), (1, 'Back')):
        text = scalar(root, 'signRealText' + suffix)
        if not isinstance(text, (bytes, type(''))):
            continue
        color = scalar(root, 'signColor' + suffix)
        glow = scalar(root, 'signGlowing' + suffix)
        rgba = None
        if isinstance(color, integer_types) and type(color) is not bool:
            color &= 0xffffffff
            rgba = tuple(((color >> shift) & 255) / 255.0 for shift in (16, 8, 0, 24))
        sides.append((side, text, rgba, glow if type(glow) is bool else None))
    return tuple(sides)
