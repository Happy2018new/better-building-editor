"""Snapshot water flow UVs for a product style, independent of native hypotheses."""
import math

from .cell import text_type
from .storage import integer_types


def direction_code(x, z):
    """Nearest eight-bit horizontal turn: 0=+x, 64=+z, 128=-x, 192=-z."""
    if any(isinstance(axis, bool) or not isinstance(axis, integer_types + (float,))
           or math.isnan(axis) or math.isinf(axis) for axis in (x, z)):
        raise ValueError('Snapshot flow direction needs two finite axes')
    if x == 0 and z == 0:
        return None
    turn = math.atan2(z, x) / (2. * math.pi)
    return int(math.floor(turn * 256 + .5)) % 256


class SnapshotFlowTop(object):
    """Map a horizontal vector onto an explicit resource template.

    The offset belongs to the product style, not the native diagnostic rule.
    A zero vector from a valid complete snapshot is a still top for this style.
    The selector retains no document/provider reference or engine state.
    """
    def __init__(self, template, rotation_offset):
        if (not isinstance(template, (bytes, text_type)) or not 0 < len(template) <= 160
                or isinstance(rotation_offset, bool) or not isinstance(rotation_offset, integer_types)
                or not -255 <= rotation_offset <= 255):
            raise ValueError('Snapshot flow top needs an explicit template orientation')
        self.template, self.rotation_offset = template, rotation_offset

    def __call__(self, vector):
        if not isinstance(vector, (tuple, list)) or len(vector) != 2:
            raise ValueError('Snapshot water flow top needs an explicit horizontal vector')
        code = direction_code(*vector)
        return (('still_water_grey', None) if code is None else
                ('flowing_water_grey', (self.template, (code + self.rotation_offset) % 256)))
