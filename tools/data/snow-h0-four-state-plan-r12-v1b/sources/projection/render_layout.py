"""Versioned virtual palette coordinates shared by CPU and render shaders."""
import math

SCHEMA_VERSION = 2
LOCAL_CONTEXT_SCHEMA_VERSION = 2
LOCAL_CONTEXT_CHUNK_SIZE = 16
MAX_LOGICAL_HEIGHT = 128
OVERLAY_BASE = 256
CONTEXT_BASE = 512
CONTEXT_STRIDE = 4
CONTEXT_CENTER = 1


def overlay_position(position):
    return (position[0], position[1] + OVERLAY_BASE, position[2])


def overlay_index(index, volume):
    """Native palettes are (z, x, y); a height shift preserves X/Z indices."""
    return index + OVERLAY_BASE * volume[0] * volume[1]


def context_position(position, neighbor=(0, 0, 0)):
    return tuple(position[axis] * CONTEXT_STRIDE + CONTEXT_CENTER + neighbor[axis] +
                 (CONTEXT_BASE if axis == 1 else 0) for axis in range(3))


def logical_position(position):
    """Decode a continuous vertex position, in logical X/Y/Z coordinates."""
    x, y, z = position
    if y >= CONTEXT_BASE:
        value = (x, y - CONTEXT_BASE, z)
        return tuple(math.floor(axis / CONTEXT_STRIDE) + axis % CONTEXT_STRIDE -
                     CONTEXT_CENTER for axis in value)
    if y >= OVERLAY_BASE:
        return (x, y - OVERLAY_BASE, z)
    return tuple(position)


def context_center(position):
    """Whether a native mesh vertex lies within the center tile's clip box."""
    if position[1] < CONTEXT_BASE - 0.5:
        return True
    value = (position[0] + 0.5, position[1] + 0.5 - CONTEXT_BASE,
             position[2] + 0.5)
    phases = tuple(axis % CONTEXT_STRIDE for axis in value)
    return all(CONTEXT_CENTER <= axis <= CONTEXT_CENTER + 1
               for axis in phases)


def native_mesh_position(position):
    """Map positive palette corners to native block-mesh coordinates."""
    return tuple(axis - 0.5 for axis in position)


def local_context_position(position, neighbor=(0, 0, 0)):
    return tuple((position[axis] % LOCAL_CONTEXT_CHUNK_SIZE) * CONTEXT_STRIDE +
                 CONTEXT_CENTER + neighbor[axis] for axis in range(3))


def local_context_center(position):
    phases = tuple((axis + 0.5) % CONTEXT_STRIDE for axis in position)
    return all(CONTEXT_CENTER <= axis <= CONTEXT_CENTER + 1 for axis in phases)


def local_context_logical(position):
    return tuple(math.floor(axis / CONTEXT_STRIDE) + axis % CONTEXT_STRIDE -
                 CONTEXT_CENTER for axis in position)
