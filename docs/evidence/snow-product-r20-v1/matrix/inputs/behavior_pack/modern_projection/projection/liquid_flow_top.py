"""Explicit, unaccepted water-top candidate; no native flow rule is assumed."""
import math

from . import block_registry, liquid_flow_top_data as source, liquid_shape_data
from .liquid_render_plan import WATER_NAMES
from .storage import integer_types


def check_version():
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != block_registry.source_version()
            or source.PALETTE_SHA256.lower() != block_registry.fingerprint().lower()
            or source.SHAPE_CANDIDATE_SHA256 != liquid_shape_data.CANDIDATE_SHA256):
        raise ValueError('Liquid flowing top candidate needs regeneration for this registry and shape source')


def rotation_code(x, z):
    """Nearest 1/256 turn: 0=+x, 64=+z, 128=-x, 192=-z; zero is unknown."""
    if any(isinstance(axis, bool) or not isinstance(axis, integer_types + (float,))
           or math.isnan(axis) or math.isinf(axis) for axis in (x, z)):
        raise ValueError('Flow direction needs two finite axes')
    if x == 0 and z == 0:
        return None
    turn = math.atan2(z, x) / (2. * math.pi)
    return int(math.floor(turn * source.ROTATION_STEPS + .5)) % source.ROTATION_STEPS


def top_uv(u, v, code):
    """Full-frame center window; inverse rotate a half-size unit square about .5."""
    if (isinstance(code, bool) or not isinstance(code, integer_types)
            or not 0 <= code < source.ROTATION_STEPS
            or any(isinstance(axis, bool) or not isinstance(axis, integer_types + (float,))
                   or not 0 <= axis <= 1 for axis in (u, v))):
        raise ValueError('Flow top UV needs unit coordinates and an eight-bit angle')
    angle = code * (2. * math.pi / source.ROTATION_STEPS)
    cosine, sine = math.cos(angle), math.sin(angle)
    x, z = u - .5, v - .5
    return (.5 + source.UV_SPAN * (cosine * x + sine * z),
            .5 + source.UV_SPAN * (-sine * x + cosine * z))


def candidate_flow_uv(document, pos, layer, value, heights):
    """Downhill four-corner gradient hypothesis, independent of native propagation.

    Flat/zero-gradient corners have unknown native direction. This candidate
    deliberately keeps the existing still top for them, including aliases and
    falling depth states. This is not evidence that the native face is still.
    """
    check_version()
    if value[0] not in WATER_NAMES or document.get_layer(pos, layer) != value:
        raise ValueError('Flow top candidate needs unchanged source-owned water')
    if (not isinstance(heights, (tuple, list)) or len(heights) != 4
            or any(isinstance(height, bool) or not isinstance(height, integer_types + (float,))
                   or not 0 <= height <= 1 for height in heights)):
        raise ValueError('Flow top candidate needs four finite unit heights')
    nw, ne, se, sw = heights
    code = rotation_code(nw + sw - ne - se, nw + ne - sw - se)
    return (('still_water_grey', None) if code is None else
            ('flowing_water_grey', (source.TEMPLATE, code)))
