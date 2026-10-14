"""Decode observed spawner configuration without rendering internal creatures."""
from .block_registry import states
from .cell import integer_types
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

SCHEMA_VERSION = 1
ENGINE_VERSION = '3.10.0.420447'
NAMES = frozenset(('minecraft:mob_spawner', 'minecraft:trial_spawner'))
PRESENT, EMPTY, UNKNOWN = 'present', 'empty', 'unknown'
_MISSING = object()
_TRIAL_DEFAULT_FIELDS = (('simultaneous_mobs', 5), ('simultaneous_mobs_added_per_player', 5),
                         ('spawn_range', 3), ('target_cooldown_length', 3), ('ticks_between_spawn', 3),
                         ('total_mobs', 5), ('total_mobs_added_per_player', 5))


def _typed_string(root, name):
    key = field_key(root, name)
    tag = root.get(key) if key is not None else None
    if not isinstance(tag, dict) or scalar(tag, '__type__') != 8:
        return _MISSING
    value = scalar(tag, '__value__')
    return value if isinstance(value, (bytes, type(u''))) else _MISSING


def _identifier(value):
    if value is _MISSING:
        return UNKNOWN
    if not value:
        return EMPTY
    # A custom entity ID is a valid configuration too; no creature allowlist.
    separator = b':' if isinstance(value, bytes) else ':'
    allowed = (b'abcdefghijklmnopqrstuvwxyz0123456789_-./:' if isinstance(value, bytes)
               else u'abcdefghijklmnopqrstuvwxyz0123456789_-./:')
    if (value.count(separator) != 1 or not all(value.split(separator)) or
            any(character not in allowed for character in value)):
        return UNKNOWN
    return PRESENT


def _weight(root, name):
    tag = root.get(field_key(root, name))
    value = scalar(root, name)
    if (not isinstance(tag, dict) or scalar(tag, '__type__') != 3 or
            not isinstance(value, integer_types) or type(value) is bool):
        return None
    return value


def _potential_presence(config):
    key = field_key(config, 'spawn_potentials')
    if key is None:
        # Absence is empty only for the complete, observed native config shape.
        for name, kind in _TRIAL_DEFAULT_FIELDS:
            tag = config.get(field_key(config, name))
            value = scalar(config, name)
            if (not isinstance(tag, dict) or scalar(tag, '__type__') != kind or
                    not isinstance(value, integer_types + (float,)) or type(value) is bool):
                return UNKNOWN
        return EMPTY
    entries = config[key]
    if not isinstance(entries, list):
        return UNKNOWN
    outcomes = []
    for entry in entries:
        root = root_payload(entry)
        if root is None:
            return UNKNOWN
        weight = _weight(root, 'weight')
        data = root_payload(root.get(field_key(root, 'data')))
        entity = root_payload(data.get(field_key(data, 'entity'))) if data is not None else None
        identity = _identifier(_typed_string(entity, 'id')) if entity is not None else UNKNOWN
        if weight is None or weight < 0 or identity == UNKNOWN:
            return UNKNOWN
        if weight > 0:
            outcomes.append(identity)
    return PRESENT if PRESENT in outcomes else EMPTY


def presence(material, actor):
    """Return no marker for other blocks and an explicit unknown for partial NBT."""
    if material[0] not in NAMES:
        return None
    root = root_payload(entity_nbt(actor))
    expected = 'MobSpawner' if material[0] == 'minecraft:mob_spawner' else 'TrialSpawner'
    if root is None or _typed_string(root, 'id') not in (expected, expected.encode('ascii')):
        return UNKNOWN
    if expected == 'MobSpawner':
        return _identifier(_typed_string(root, 'EntityIdentifier'))
    record = states(material)
    ominous = record.get('ominous') if record is not None else None
    if type(ominous) is not bool:
        return UNKNOWN
    config = root_payload(root.get(field_key(root, 'ominous_config' if ominous else 'normal_config')))
    if config is None:
        return UNKNOWN
    configured = _potential_presence(config)
    spawn_key = field_key(root, 'spawn_data')
    if spawn_key is None:
        return configured
    active = root_payload(root[spawn_key])
    if active is None:
        return UNKNOWN
    identity = _identifier(_typed_string(active, 'TypeId'))
    weight = _weight(active, 'Weight')
    if weight is None or weight < 0 or identity == UNKNOWN:
        return UNKNOWN
    selected = identity if weight > 0 else EMPTY
    return selected if selected == configured else UNKNOWN
