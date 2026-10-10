"""Per-tile view depth carried by an adjacent transparent UI image.

RGB is data; alpha remains the workspace fade. No UI layer mutation is needed
when the camera crosses an octant or moves through the building.
"""
import math
from .biomes import shader_index


def depth_color(distance, biome, layout=None):
    # Signed 16-bit fixed point, 1/64 block. All points of a 64x128x64
    # document fit; fully clipped tiles never require a packet outside it.
    value = max(0, min(65535, int(math.floor(distance * 64. + .5)) + 32768))
    if layout is not None:
        from .render_layout import MAX_LOGICAL_HEIGHT, OVERLAY_BASE
        height, native_height = layout
        if not 1 <= height <= MAX_LOGICAL_HEIGHT or native_height not in (height, height + OVERLAY_BASE):
            raise ValueError('Unsupported preview render layout')
        # Dyadic channels keep depth and native centering exact in float32.
        # The quarter-step red tag distinguishes this packet from old RGB.
        packet = height + (OVERLAY_BASE if native_height != height else 0)
        return ((208 + shader_index(biome) + .25) / 255., packet / 1024., value / 65536.)
    return ((208 + shader_index(biome)) / 255., (value >> 8) / 255., (value & 255) / 255.)


def tile_layer(key):
    # Unique, stable pairs: state image immediately before both model buffers.
    # There are 4x8x4 tiles; the highest model layer is 304, below overlays.
    x, y, z = key
    return 50 + 2 * (x * 32 + y * 4 + z)
