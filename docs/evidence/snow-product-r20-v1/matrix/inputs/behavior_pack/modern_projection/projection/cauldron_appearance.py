"""Pure cauldron shell/overlay data decoding.

The native cauldron actor remains the authority for the shell.  This module
only extracts the state and the small set of observed, visible NBT fields that
the future custom liquid mesh will need.  It deliberately does not know any
mesh coordinates, resource names, potion colour table, or SDK APIs.
"""
from __future__ import unicode_literals
from collections import namedtuple

from .cell import freeze, integer_types, thaw, text_type
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

SCHEMA_VERSION = 1
CAULDRON_MATERIALS = frozenset((
    'minecraft:cauldron',
    'minecraft:water_cauldron',
    'minecraft:lava_cauldron',
    'minecraft:powder_snow_cauldron',
))
LIQUIDS = frozenset(('water', 'lava', 'powder_snow'))
COLOR_SOURCES = frozenset(('none', 'potion', 'custom_color'))

CauldronShell = namedtuple('CauldronShell', ('material', 'renderer'))
CauldronOverlay = namedtuple('CauldronOverlay', (
    'liquid', 'fill_level', 'color_source', 'potion_id', 'potion_type',
    'custom_color'))
CauldronAppearance = namedtuple('CauldronAppearance', (
    'schema_version', 'material', 'shell', 'overlay', 'nbt_snapshot'))


def _liquid(value):
    if isinstance(value, bytes):
        try:
            value = value.decode('utf8')
        except UnicodeError:
            return None
    return value if value in LIQUIDS else None


def _integer(value):
    return isinstance(value, integer_types) and type(value) is not bool


def _state_value(states, name):
    if not isinstance(states, dict):
        return None
    key = name if name in states else name.encode('utf8')
    return states.get(key)


def _field_integer(root, name):
    """Read an optional scalar without changing its typed NBT representation."""
    if root is None:
        return None
    key = field_key(root, name)
    if key is None:
        return None
    value = scalar(root, name)
    return value if _integer(value) else None


def _root_for_actor(actor):
    if actor is None:
        return None
    payload = entity_nbt(actor)
    if payload is None:
        return None
    root = root_payload(payload)
    if not isinstance(root, dict):
        return None
    identity = scalar(root, 'id')
    return root if identity in ('Cauldron', b'Cauldron') else None


def _material_name(material):
    if not isinstance(material, (tuple, list)) or not material:
        return None
    name = material[0]
    if isinstance(name, bytes):
        try:
            name = name.decode('utf8')
        except UnicodeError:
            return None
    return name if isinstance(name, text_type) else None


def decode_cauldron_appearance(material, states, actor=None):
    """Decode a cauldron into a native shell and an independent liquid overlay.

    ``material`` and ``states`` identify the native shell and its six-step fill
    state.  ``actor`` may be a raw typed NBT compound or an actor envelope.  A
    copy of the complete actor payload is retained as ``nbt_snapshot`` so the
    renderer can never accidentally turn appearance extraction into a storage
    rewrite.  Optional malformed NBT fields are ignored conservatively.

    The function returns ``None`` for non-cauldron materials or unverified
    state records.  It never supplies a default fill height or a guessed
    potion colour.
    """
    if (not isinstance(material, (tuple, list)) or len(material) != 2 or
            not _integer(material[1]) or not 0 <= material[1] <= 32767):
        return None
    name = _material_name(material)
    if name not in CAULDRON_MATERIALS:
        return None
    liquid = _liquid(_state_value(states, 'cauldron_liquid'))
    fill_level = _state_value(states, 'fill_level')
    if liquid is None or not _integer(fill_level) or not 0 <= fill_level <= 6:
        return None

    root = _root_for_actor(actor)
    potion_id = _field_integer(root, 'PotionId')
    potion_type = _field_integer(root, 'PotionType')
    custom_color = _field_integer(root, 'CustomColor')
    if custom_color is not None:
        color_source = 'custom_color'
    elif potion_id is not None or potion_type is not None:
        color_source = 'potion'
    else:
        color_source = 'none'

    overlay = CauldronOverlay(liquid, fill_level, color_source,
                              potion_id, potion_type, custom_color)
    # freeze() is the same bounded immutable NBT representation used by the
    # cell store.  Keeping it here makes the adapter side-effect free while
    # retaining unknown tags for a later renderer or serializer.
    snapshot = None if actor is None else freeze(actor)
    shell = CauldronShell(tuple(material), 'native')
    return CauldronAppearance(SCHEMA_VERSION, tuple(material), shell, overlay,
                              snapshot)


def nbt_snapshot(appearance):
    """Return a detached copy of the original actor payload, if retained."""
    if not isinstance(appearance, CauldronAppearance):
        raise TypeError('Expected a CauldronAppearance')
    return None if appearance.nbt_snapshot is None else thaw(appearance.nbt_snapshot)

