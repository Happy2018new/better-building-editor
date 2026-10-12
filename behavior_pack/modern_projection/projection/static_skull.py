"""Closed vanilla skull meshes for observed player-placement poses."""
from __future__ import unicode_literals
from . import block_registry as registry
from . import static_skull_data as source
from .block_registry import states
from .native_appearance import angle, validate_source
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt, render_actor

SKULL_MATERIALS = ('minecraft:skeleton_skull', 'minecraft:wither_skeleton_skull',
                   'minecraft:zombie_head', 'minecraft:creeper_head')
SKULL_POSES = tuple('floor_' + str(index) for index in range(16)) + tuple(
    'wall_' + str(face) for face in (2, 3, 4, 5))
SKULL_PROXIES = dict((name, dict((pose, 'modern_projection:preview_' +
    name.split(':')[1] + '_' + pose) for pose in SKULL_POSES)) for name in SKULL_MATERIALS)


def _validate_source():
    if (getattr(source, 'SCHEMA_VERSION', None) != 1 or
            source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256.lower() != registry.fingerprint().lower()):
        raise ValueError('Native skull models need regeneration for this block registry')
    validate_source()


def skull_proxy(material, actor):
    names = SKULL_PROXIES.get(material[0])
    if names is None:
        return None
    record = states(material)
    if record is None:
        return None
    facing = record.get('facing_direction')
    if facing in (2, 3, 4, 5):
        _validate_source()
        return (names['wall_' + str(facing)], 0)
    if facing != 1:
        return None
    root = root_payload(entity_nbt(actor))
    renderer = root_payload(render_actor(actor))
    rotation = None
    if root is not None and scalar(root, 'id') in ('Skull', b'Skull'):
        tag = root.get(field_key(root, 'Rotation'))
        if not isinstance(tag, dict) or scalar(tag, '__type__') != 5:
            return None
        rotation = scalar(root, 'Rotation')
    if rotation is None:
        rotation = scalar(renderer, 'rotation') if renderer is not None else 0.
    if not angle(rotation):
        return None
    step = rotation % 360. / 22.5
    index = int(round(step))
    if abs(step - index) > .00001:
        return None
    _validate_source()
    return (names['floor_' + str(index % 16)], 0)
