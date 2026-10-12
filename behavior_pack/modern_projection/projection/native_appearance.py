"""Rules backed by the versioned native player-placement observations."""
from __future__ import unicode_literals
import math
from . import block_registry as registry
from .cell import integer_types

SCHEMA_VERSION = 2
SOURCE_VERSION = 'NEMC 3.9.0.401155'
PALETTE_SHA256 = '6b2d9e961e934a745f5ab30d697cf22fb463fd3792d371a6dd42cb4342062f01'
SOURCE_SHA256 = '2d024ca2f196e88a4ec7ac1ff5e455ca42d901381142a4dd00c53e4b48c307ce'
SKULL_NAMES = frozenset('minecraft:' + name for name in (
    'skeleton_skull', 'wither_skeleton_skull', 'zombie_head', 'player_head',
    'creeper_head', 'dragon_head', 'piglin_head'))
FRAME_NAMES = frozenset(('minecraft:frame', 'minecraft:glow_frame'))


def validate_source():
    if (SCHEMA_VERSION != 2 or SOURCE_VERSION != registry.source_version() or
            PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native appearance rules need observations for this block registry')


def angle(value):
    return (isinstance(value, integer_types + (float,)) and type(value) is not bool
            and not math.isnan(value) and not math.isinf(value))


def transform_yaw(value, operation):
    """Native yaw zero is +Z; preserve the observed [-180, 180) convention."""
    validate_source()
    if operation.startswith('rotate_y'):
        value += int(operation[8:])
    elif operation == 'mirror_x':
        value = -value
    elif operation == 'mirror_z':
        value = 180 - value
    else:
        return value
    return (value + 180) % 360 - 180


def transform_frame_rotation(value, facing, operation):
    """Express the transformed item's top vector in its new face-local plane.

    Wall frames use world up; top/bottom frames use north/south respectively.
    Angles turn clockwise when looking at the displayed surface. Reflections
    preserve the representable item direction, not reflected item artwork.
    """
    from . import frame_rotation_data as source
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native frame rotation rules need observations for this block registry')
    if operation.startswith('rotate_y'):
        if facing > 1:
            return value
        return (value + int(operation[8:]) * (1 if facing == 1 else -1)) % 360
    if operation == 'mirror_x' or operation == 'mirror_z' and facing > 1:
        return -value % 360
    if operation in ('mirror_y', 'mirror_z'):
        return (180 - value) % 360
    return value
