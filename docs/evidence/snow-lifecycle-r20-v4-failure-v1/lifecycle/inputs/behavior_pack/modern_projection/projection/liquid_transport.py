"""Four-cell payload encoding; all shape and UV decisions belong to the provider."""
from collections import namedtuple
import math
from .storage import integer_types

PAYLOAD_TAG = 39686.
PAYLOAD_VERSION = 2
PREVIEW_TAG_BYTE = 134
DEPTH_DENOMINATOR = 64
MAX_DEPTH_ERROR = .5 / DEPTH_DENOMINATOR
UNSPECIFIED_OPACITY = -1.
CELLS_PER_GROUP = 4
HEIGHT_DENOMINATOR = 255
MAX_HEIGHT_ERROR = .5 / HEIGHT_DENOMINATOR
TEXTURE_KEYS = frozenset(('still_water_grey', 'flowing_water_grey',
                          'still_lava', 'flowing_lava'))
FACE_NAMES = ('top', 'north', 'south', 'west', 'east', 'bottom')

RenderGroup = namedtuple('RenderGroup', 'key model_name origin uniforms')


def _integer(value, low, high, label):
    if isinstance(value, bool) or not isinstance(value, integer_types) or not low <= value <= high:
        raise ValueError('Invalid liquid ' + label)
    return value


def _unit(value, label):
    if (isinstance(value, bool) or not isinstance(value, integer_types + (float,))
            or not 0. <= value <= 1.):
        raise ValueError('Invalid liquid ' + label)
    return float(value)


def _position(value, label):
    if not isinstance(value, tuple) or len(value) != 3:
        raise ValueError('Liquid ' + label + ' must be a three-integer tuple')
    if any(isinstance(axis, bool) or not isinstance(axis, integer_types) for axis in value):
        raise ValueError('Invalid liquid ' + label)
    return value


def _uv(value):
    if value is None:
        return None, 0
    if not isinstance(value, tuple) or len(value) != 2 or not value[0]:
        raise ValueError('Liquid flow UV requires an explicit template and rotation code')
    return value[0], _integer(value[1], 0, 255, 'UV rotation')


def preview_tag(distance):
    if (isinstance(distance, bool) or not isinstance(distance, integer_types + (float,))
            or math.isinf(distance) or math.isnan(distance)
            or not -512. <= distance <= 511.984375):
        raise ValueError('Liquid preview distance exceeds the signed16 depth range')
    code = int(math.floor(distance * DEPTH_DENOMINATOR + 32768. + .5))
    return float((code << 8) | PREVIEW_TAG_BYTE)


def appearance_uniform(color, opacity, projection_opacity, preview_distance=None):
    """Keep unspecified material opacity distinct from the projection opacity."""
    if not isinstance(color, tuple) or len(color) != 3:
        raise ValueError('Liquid tint requires three RGB bytes')
    rgb = tuple(_integer(channel, 0, 255, 'tint channel') for channel in color)
    alpha = UNSPECIFIED_OPACITY if opacity is None else _unit(opacity, 'material opacity')
    packed_tint = (rgb[0] << 16) | (rgb[1] << 8) | rgb[2]
    tag = PAYLOAD_TAG if preview_distance is None else preview_tag(preview_distance)
    return (tag, alpha, float(packed_tint), _unit(projection_opacity, 'projection opacity'))


def with_preview_distance(group, distance):
    validate_uniforms(group.uniforms)
    tag = PAYLOAD_TAG if distance is None else preview_tag(distance)
    if group.uniforms[3][0] == tag:
        return group
    appearance = (tag,) + group.uniforms[3][1:]
    return group._replace(uniforms=group.uniforms[:3] + (appearance,))


def pack_group(origin, surfaces, color, opacity, projection_opacity, preview_distance=None):
    """Encode local address6 + faces6 + rotation8; omit unused slots with faces=0.

    Heights use nearest 8-bit codes with maximum normalized error 1/510.
    This quantization bound is not acceptance of a native height formula.
    """
    origin = _position(origin, 'group origin')
    if any(axis % 4 for axis in origin):
        raise ValueError('Liquid group origin must align with a four-cube')
    if not isinstance(surfaces, tuple) or not 1 <= len(surfaces) <= CELLS_PER_GROUP:
        raise ValueError('Liquid groups require one to four surfaces')
    addresses, height_pairs, occupied = [], [], set()
    family = None
    for surface in surfaces:
        position = _position(surface.position, 'surface position')
        local = tuple(position[axis] - origin[axis] for axis in range(3))
        if any(axis < 0 or axis >= 4 for axis in local):
            raise ValueError('Liquid surface is outside its group')
        if isinstance(surface.layer, bool) or surface.layer not in ('foreground', 'background', 0, 1):
            raise ValueError('Invalid liquid logical layer')
        identity = (position, surface.layer)
        if identity in occupied:
            raise ValueError('Duplicate liquid logical surface')
        occupied.add(identity)
        if surface.texture_key not in TEXTURE_KEYS:
            raise ValueError('Liquid texture must be chosen explicitly by the provider')
        template, rotation = _uv(surface.flow_uv)
        material = (surface.texture_key, template)
        if family is not None and family != material:
            raise ValueError('Liquid group mixes texture or UV templates')
        family = material
        faces = _integer(surface.faces, 0, 63, 'face mask')
        if not isinstance(surface.heights, tuple) or len(surface.heights) != 4:
            raise ValueError('Liquid surface requires four explicit corner heights')
        heights = tuple(int(_unit(value, 'corner height') * HEIGHT_DENOMINATOR + .5)
                        for value in surface.heights)
        address = local[0] + 4 * local[2] + 16 * local[1]
        addresses.append(float(address | (faces << 6) | (rotation << 12)))
        height_pairs.extend((float(heights[0] | (heights[1] << 8)),
                             float(heights[2] | (heights[3] << 8))))
    addresses.extend([0.] * (CELLS_PER_GROUP - len(surfaces)))
    height_pairs.extend([0.] * (2 * (CELLS_PER_GROUP - len(surfaces))))
    return (tuple(addresses), tuple(height_pairs[:4]), tuple(height_pairs[4:]),
            appearance_uniform(color, opacity, projection_opacity, preview_distance))


def validate_uniforms(uniforms):
    if not isinstance(uniforms, tuple) or len(uniforms) != 4:
        raise ValueError('Liquid rendering requires four vec4 groups')
    for group in uniforms:
        if not isinstance(group, tuple) or len(group) != 4:
            raise ValueError('Invalid liquid vec4 group')
        if any(isinstance(value, bool) or not isinstance(value, integer_types + (float,))
               or not -16777215. <= value <= 16777215. for value in group):
            raise ValueError('Liquid uniforms require finite float-exact values')
    tag = uniforms[3][0]
    if tag != PAYLOAD_TAG and not (tag == int(tag) and 0 <= tag <= 16777215
                                   and int(tag) % 256 == PREVIEW_TAG_BYTE):
        raise ValueError('Liquid payload tag does not match its material')
    if any(value != int(value) or not 0 <= value < 1048576 for value in uniforms[0]):
        raise ValueError('Liquid cell codes must contain address6 + faces6 + rotation8')
    if any(value != int(value) or not 0 <= value <= 65535 for group in uniforms[1:3] for value in group):
        raise ValueError('Liquid height pairs must contain two unsigned bytes')
    opacity, tint, projection = uniforms[3][1:]
    if opacity != UNSPECIFIED_OPACITY:
        _unit(opacity, 'material opacity')
    if tint != int(tint) or not 0 <= tint <= 16777215:
        raise ValueError('Liquid tint must contain three unsigned bytes')
    _unit(projection, 'projection opacity')
    return uniforms
