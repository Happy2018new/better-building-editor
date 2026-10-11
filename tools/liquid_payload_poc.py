"""Isolated, quantized triangle carriers; no native liquid rule is inferred."""
import math

SCHEMA_VERSION = 1
CHUNK_SIDE = 4
CELLS_PER_BATCH = CHUNK_SIDE ** 3
FACE_NAMES = ('top', 'bottom', 'north', 'south', 'west', 'east')
ALL_FACES = (1 << len(FACE_NAMES)) - 1
PROXY_PREFIX = 'modern_projection:liquid_payload_poc_h'
PAYLOAD_TEXTURE = 'modern_projection_liquid_payload_poc'
ACTOR_TAG = 39683.0
FAMILIES = ('water', 'lava')


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def levels(height_bits):
    if not _integer(height_bits) or height_bits not in (6, 8):
        raise ValueError('The isolated carrier supports only six or eight height bits')
    return 1 << height_bits


def quantize(height, height_bits=8):
    count = levels(height_bits)
    if (isinstance(height, bool) or not isinstance(height, (float, int)) or
            not 0.0 <= height <= 1.0):
        raise ValueError('A finite, explicitly supplied unit height is required')
    return int(math.floor(height * (count - 1) + 0.5))


def proxy_name(height_code):
    if not _integer(height_code) or not 0 <= height_code < 256:
        raise ValueError('Invalid static third-corner height code')
    return PROXY_PREFIX + ('%03d' % height_code)


def logical_index(position):
    if (not isinstance(position, (tuple, list)) or len(position) != 3 or
            any(not _integer(axis) or not 0 <= axis < CHUNK_SIDE for axis in position)):
        raise ValueError('A local integer position in a four-cubed batch is required')
    x, y, z = position
    return (y * CHUNK_SIDE + z) * CHUNK_SIDE + x


def logical_position(index):
    if not _integer(index) or not 0 <= index < CELLS_PER_BATCH:
        raise ValueError('Invalid logical carrier cell')
    return index % 4, index // 16, index // 4 % 4


class LiquidSurface(object):
    """Heights ordered (00, 10, 11, 01); faces are caller-owned evidence."""
    def __init__(self, position, heights, faces=ALL_FACES, family='water'):
        if (not isinstance(position, (tuple, list)) or len(position) != 3 or
                any(not _integer(axis) for axis in position)):
            raise ValueError('Surface positions must be three integers')
        if not isinstance(heights, (tuple, list)) or len(heights) != 4:
            raise ValueError('Four independently supplied corner heights are required')
        for height in heights:
            quantize(height)
        if not _integer(faces) or not 0 <= faces <= ALL_FACES or family not in FAMILIES:
            raise ValueError('Invalid explicit face mask or liquid family')
        self.position, self.heights = tuple(position), tuple(heights)
        self.faces, self.family = faces, family


def face_payloads(surface, height_bits=8):
    h00, h10, h11, h01 = tuple(quantize(h, height_bits) for h in surface.heights)
    if surface.faces & 1:
        yield 0, h00, h10, h11
        yield 1, h00, h11, h01
    if surface.faces & 2:
        yield 6, 0, 0, 0
    # Preserve the source up-quad winding when turning it into each outer wall.
    for face, kind, left, right in ((2, 2, h00, h10), (3, 3, h11, h01),
                                   (4, 4, h01, h00), (5, 5, h10, h11)):
        if surface.faces & (1 << face):
            yield kind, 0, left, right


class CarrierBatch(object):
    def __init__(self, origin, family, height_bits):
        self.origin, self.family, self.height_bits = tuple(origin), family, height_bits
        self.carriers, self.source_positions = [], set()

    def add(self, surface):
        if surface.family != self.family:
            raise ValueError('A carrier batch has one independently bound native texture')
        local = tuple(surface.position[axis] - self.origin[axis] for axis in range(3))
        index = logical_index(local)
        if surface.position in self.source_positions:
            raise ValueError('A surface cannot be silently overlaid with another surface')
        self.source_positions.add(surface.position)
        for kind, third, left, right in face_payloads(surface, self.height_bits):
            self.carriers.append(((left, index + kind * CELLS_PER_BATCH, right), third))

    def palette(self):
        if not self.carriers:
            return {'volume': (1, 1, 1), 'common': {}, 'extra': {}, 'actor': {}}
        extent = tuple(max(row[0][axis] for row in self.carriers) + 1 for axis in range(3))
        sx, sy, sz = extent
        common = {}
        for (x, y, z), height in self.carriers:
            index = (y * sx + x) * sz + z
            common.setdefault((proxy_name(height), 0), []).append(index)
        for indices in common.values():
            indices.sort()
        return {'volume': (sz, sx, sy), 'common': common, 'extra': {}, 'actor': {}}

    def diagnostic(self):
        volume = self.palette()['volume']
        count = levels(self.height_bits)
        return {'schema_version': SCHEMA_VERSION, 'origin': self.origin,
                'family': self.family, 'height_bits': self.height_bits,
                'max_quantization_error_blocks': 0.5 / (count - 1),
                'source_cells': len(self.source_positions), 'carrier_cells': len(self.carriers),
                'palette_volume': volume, 'palette_volume_indices': volume[0] * volume[1] * volume[2],
                'native_integer_coordinate_max': tuple(axis - 1 for axis in (volume[1], volume[2], volume[0])),
                'native_geometry_accepted': False, 'accuracy_accepted': False,
                'production_memory_accepted': False, 'animated_sampling_accepted': False}


def batches(surfaces, height_bits=8):
    levels(height_bits)
    groups = {}
    for surface in surfaces:
        origin = tuple(axis // CHUNK_SIDE * CHUNK_SIDE for axis in surface.position)
        key = origin, surface.family
        group = groups.get(key)
        if group is None:
            group = groups[key] = CarrierBatch(origin, surface.family, height_bits)
        group.add(surface)
    return tuple(groups[key] for key in sorted(groups))


def decode_vertex(carrier, third_code, source_corner, height_bits=8):
    """Host oracle for the shader; accepts only actual source quad corners."""
    count = levels(height_bits)
    left, address, right = carrier
    if (any(not _integer(code) for code in (left, address, right, third_code)) or
            not 0 <= left < count or not 0 <= right < count or
            not 0 <= third_code < count or not 0 <= address < 7 * CELLS_PER_BATCH or
            tuple(source_corner) not in ((0, 0), (1, 0), (1, 1), (0, 1))):
        raise ValueError('Invalid carrier vertex')
    kind, index = divmod(address, CELLS_PER_BATCH)
    x, y, z = logical_position(index)
    u, v = source_corner
    if kind < 2:
        if not u:
            point = 0.0, third_code / float(count - 1), 0.0
        elif not v:
            point = 1.0, left / float(count - 1), float(kind)
        else:
            point = 1.0 - kind, right / float(count - 1), 1.0
    elif kind == 6:
        point = float(1 - u), 0.0, float(v)
    else:
        height = v * (left * (1 - u) + right * u) / float(count - 1)
        point = {2: (u, height, 0), 3: (1 - u, height, 1),
                 4: (0, height, 1 - u), 5: (1, height, u)}[kind]
    return tuple(base + value for base, value in zip((x, y, z), point))
