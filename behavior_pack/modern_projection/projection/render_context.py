"""Prepare one missing-only mesh while retaining each cell's native neighbors."""
from collections import OrderedDict
from .cell import AIR, actor_data, background, foreground
from .geometry_palette import prepare_palette
from .entity_render import document_chest_part
from .large_preview import MAX_SURFACE_BLOCKS
from .nbt_spatial import rebase
from .render_layout import (CONTEXT_BASE, CONTEXT_CENTER, CONTEXT_STRIDE,
                            MAX_LOGICAL_HEIGHT, OVERLAY_BASE, context_position)
from .storage import integer_types

NEIGHBORS = tuple((x, y, z) for y in (-1, 0, 1)
                  for x in (-1, 0, 1) for z in (-1, 0, 1))
MAX_CONTEXT_CHUNK_CACHE = 32
TARGETS_PER_UNIT = 16


def _position(index, volume):
    z_size, x_size, unused_y = volume
    return (index // z_size % x_size, index // (z_size * x_size), index % z_size)


def _index(position, volume):
    return (position[1] * volume[1] + position[0]) * volume[0] + position[2]


def _targets(source, targets):
    volume = source.get('volume')
    if (volume is None or len(volume) != 3 or min(volume) <= 0 or
            volume[2] > MAX_LOGICAL_HEIGHT or targets.get('volume') != volume):
        raise ValueError('Context palettes require matching supported logical volumes')
    total = volume[0] * volume[1] * volume[2]
    indices = set(index for layer in ('common', 'extra')
                  for value, entries in targets.get(layer, {}).items()
                  if value != AIR for index in entries)
    if any(index < 0 or index >= total for index in indices):
        raise ValueError('Context target is outside its logical palette volume')
    return tuple(_position(index, volume) for index in sorted(indices))


def _cells(prepared, logical_volume):
    total = logical_volume[0] * logical_volume[1] * logical_volume[2]
    cells, overlays = {}, {}
    for layer in ('common', 'extra'):
        for value, indices in prepared.get(layer, {}).items():
            for index in indices:
                if 0 <= index < total:
                    cells.setdefault(index, {})[layer] = value
                elif layer == 'common':
                    original = index - OVERLAY_BASE * logical_volume[0] * logical_volume[1]
                    if not 0 <= original < total:
                        raise ValueError('Unrecognized virtual position in logical source palette')
                    overlays[original] = value
    for name, actors in prepared.get('actor', {}).items():
        for index, actor in actors.items():
            if index in cells:
                cells[index]['actor'] = (name, actor)
    return cells, overlays


def _put(data, cell, position, original):
    index = _index(position, data['volume'])
    delta = tuple(position[axis] - original[axis] for axis in range(3))
    _put_encoded(data, cell, index, delta)


def _put_encoded(data, cell, index, delta):
    for layer in ('common', 'extra'):
        value = cell.get(layer)
        if value is not None and value != AIR:
            data[layer].setdefault(value, []).append(index)
    actor = cell.get('actor')
    if actor is not None:
        name, payload = actor
        data['actor'].setdefault(name, {})[index] = rebase(payload, delta)


def prepare_context_palette(source, targets):
    """Return a final native render palette; do not prepare it a second time.

    ``source`` contains the whole logical document. ``targets`` contains only
    visible/missing cells, in the same original native (z, x, y) volume.
    Neighbors use document data, never reads of the target Minecraft world.
    """
    positions = _targets(source, targets)
    if len(positions) > MAX_SURFACE_BLOCKS:
        raise ValueError('Context targets exceed the visible block budget')
    if not positions:
        data = dict(source)
        data.update(common={}, extra={}, actor={}, states={}, extraStates={})
        return data
    logical_volume = source['volume']
    prepared = prepare_palette(source)
    cells, overlays = _cells(prepared, logical_volume)
    volume = (CONTEXT_STRIDE * (max(pos[2] for pos in positions) + 1),
              CONTEXT_STRIDE * (max(pos[0] for pos in positions) + 1),
              CONTEXT_BASE + CONTEXT_STRIDE * (max(pos[1] for pos in positions) + 1))
    data = dict(prepared)
    data.update(volume=volume, common={}, extra={}, actor={})
    for target in positions:
        target_index = _index(target, logical_volume)
        if target_index not in cells:
            raise ValueError('Context target is absent from the complete source palette')
        for neighbor in NEIGHBORS:
            original = tuple(target[axis] + neighbor[axis] for axis in range(3))
            if any(original[axis] < 0 or original[axis] >= logical_volume[(1, 2, 0)[axis]]
                   for axis in range(3)):
                continue
            cell = cells.get(_index(original, logical_volume))
            if cell is None:
                continue
            _put(data, cell, context_position(target, neighbor), original)
        overlay = overlays.get(target_index)
        if overlay is not None:
            pos = (target[0], target[1] + OVERLAY_BASE, target[2])
            data['common'].setdefault(overlay, []).append(_index(pos, volume))
    for layer in ('common', 'extra'):
        for indices in data[layer].values():
            indices.sort()
    for key, layer in (('states', 'common'), ('extraStates', 'extra')):
        data[key] = dict((value, record) for value, record in prepared.get(key, {}).items()
                         if value in data[layer])
    return data


class ContextPaletteBuilder(object):
    """Read snapshot chunks directly and yield between small preparation units."""
    def __init__(self, document, targets):
        self.document, self.targets = document, targets
        sx, sy, sz = document.size
        self.logical_volume = (sz, sx, sy)
        if (tuple(targets.get('volume', ())) != self.logical_volume or
                not 0 < sy <= MAX_LOGICAL_HEIGHT):
            raise ValueError('Context palettes require matching supported logical volumes')
        self.cache, self.data = {}, None
        self.chunk_cache = OrderedDict()
        self.positions = []

    def material(self, x, y, z):
        key = (x >> 4, y >> 4, z >> 4)
        chunk = self.chunk_cache.get(key)
        if chunk is None:
            chunk = self.document.blocks.chunks.get(key, 0)
            if not isinstance(chunk, integer_types):
                chunk = tuple(chunk)
            # Bound expanded Python integers even for large sparse snapshots.
            if len(self.chunk_cache) == MAX_CONTEXT_CHUNK_CACHE:
                self.chunk_cache.popitem(last=False)
            self.chunk_cache[key] = chunk
        index = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        identity = chunk if isinstance(chunk, integer_types) else chunk[index]
        if not identity:
            return None
        value = self.document.blocks.palette[identity]
        front, back, actor = foreground(value), background(value), actor_data(value)
        part = document_chest_part(self.document, (x, y, z), front)
        cache_key = identity if part is None else (identity, part)
        if cache_key in self.cache:
            return self.cache[cache_key]
        source = {'volume': (1, 1, 1), 'common': {}, 'extra': {}, 'actor': {}}
        if front != AIR:
            source['common'][front] = [0]
        if back != AIR:
            source['extra'][back] = [0]
        if actor is not None:
            source['actor'][front[0]] = {0: actor}
        rendered = prepare_palette(source, {(front[0], 0): part} if part is not None else None)
        cells, overlays = _cells(rendered, (1, 1, 1))
        result = (cells.get(0), overlays.get(0), rendered['states'], rendered['extraStates'])
        self.cache[cache_key] = result
        if self.data is not None:
            self.data['states'].update(result[2])
            self.data['extraStates'].update(result[3])
        return result

    def collect(self):
        total = self.logical_volume[0] * self.logical_volume[1] * self.logical_volume[2]
        seen, units = set(), 0
        for layer in ('common', 'extra'):
            for value, indices in self.targets.get(layer, {}).items():
                if value == AIR:
                    continue
                for index in indices:
                    if index < 0 or index >= total:
                        raise ValueError('Context target is outside its logical palette volume')
                    if index not in seen:
                        seen.add(index)
                        self.positions.append(_position(index, self.logical_volume))
                    units += 1
                    if units % 128 == 0:
                        yield True
        if len(self.positions) > MAX_SURFACE_BLOCKS:
            raise ValueError('Context targets exceed the visible block budget')
        yield True

    def initialize(self):
        if self.positions:
            volume = (CONTEXT_STRIDE * (max(pos[2] for pos in self.positions) + 1),
                      CONTEXT_STRIDE * (max(pos[0] for pos in self.positions) + 1),
                      CONTEXT_BASE + CONTEXT_STRIDE * (max(pos[1] for pos in self.positions) + 1))
        else:
            volume = self.logical_volume
        self.data = {'volume': volume, 'common': {}, 'extra': {}, 'actor': {},
                     'states': {}, 'extraStates': {}, 'void': False, 'eliminateAir': True}
        self.neighbors = tuple((x, y, z, (y * volume[1] + x) * volume[0] + z)
                               for x, y, z in NEIGHBORS)
        for result in self.cache.values():
            self.data['states'].update(result[2])
            self.data['extraStates'].update(result[3])

    def put_target(self, target):
        tx, ty, tz = target
        center = self.material(tx, ty, tz)
        if center is None or center[0] is None:
            raise ValueError('Context target is absent from the complete source palette')
        cx = tx * CONTEXT_STRIDE + CONTEXT_CENTER
        cy = ty * CONTEXT_STRIDE + CONTEXT_CENTER + CONTEXT_BASE
        cz = tz * CONTEXT_STRIDE + CONTEXT_CENTER
        center_index = _index((cx, cy, cz), self.data['volume'])
        delta = (cx - tx, cy - ty, cz - tz)
        sx, sy, sz = self.document.size
        for nx, ny, nz, index_delta in self.neighbors:
            x, y, z = tx + nx, ty + ny, tz + nz
            if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
                continue
            rendered = center if nx == ny == nz == 0 else self.material(x, y, z)
            if rendered is None or rendered[0] is None:
                continue
            # All 27 cells move by the same delta into this target's tile.
            _put_encoded(self.data, rendered[0], center_index + index_delta, delta)
        if center[1] is not None:
            pos = (target[0], target[1] + OVERLAY_BASE, target[2])
            self.data['common'].setdefault(center[1], []).append(_index(pos, self.data['volume']))

    def prepare(self):
        for unused in self.collect():
            yield True
        self.initialize()
        for number, target in enumerate(self.positions, 1):
            self.put_target(target)
            if number % TARGETS_PER_UNIT == 0:
                yield True
        if self.positions and len(self.positions) % TARGETS_PER_UNIT:
            yield True
        for key, layer in (('states', 'common'), ('extraStates', 'extra')):
            self.data[key] = dict((value, record) for value, record in self.data[key].items()
                                  if value in self.data[layer])


def prepare_document_context(document, targets):
    """Synchronously adapt a small palette without serializing the whole source."""
    builder = ContextPaletteBuilder(document, targets)
    for unused in builder.prepare():
        pass
    return builder.data
