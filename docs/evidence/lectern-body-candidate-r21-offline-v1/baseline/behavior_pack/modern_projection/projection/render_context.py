"""Prepare one missing-only mesh while retaining each cell's native neighbors."""
from collections import OrderedDict
from .cell import AIR, actor_data, background, foreground
from .geometry_palette import prepare_palette
from .entity_render import CHEST_PROXIES, document_chest_part
from .static_bed import document_bed_color
from .large_preview import MAX_SURFACE_BLOCKS
from .native_layers import normalize_palette_layers
from .nbt_spatial import field_key, rebase
from .render_layout import (CONTEXT_BASE, CONTEXT_CENTER, CONTEXT_STRIDE,
                            MAX_LOGICAL_HEIGHT, OVERLAY_BASE, context_position)
from .storage import integer_types
from .plant_position import position_sensitive, render_origin as validate_render_origin
from .native_render_profile import coordinate_mode, profile_identity
from .static_table import context_cell, independent_body

NEIGHBORS = tuple((x, y, z) for y in (-1, 0, 1)
                  for x in (-1, 0, 1) for z in (-1, 0, 1))
MAX_CONTEXT_CHUNK_CACHE = 32
TARGETS_PER_UNIT = 16
_NOT_RENDERED = object()
LOCAL_NEIGHBORS = tuple((x, y, z, (y * 64 + x) * 64 + z)
                        for x, y, z in NEIGHBORS)


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


def _native_actor_mesh(cell, native_render_profile=None):
    actor = cell.get('actor')
    if actor is None or not isinstance(actor[1], dict):
        return False
    material = cell.get('common')
    if material is None:
        return False
    mode = coordinate_mode(native_render_profile, material, actor[1])
    if mode is not None:
        return mode == 'model_local'
    if material[0] == 'minecraft:decorated_pot':
        return field_key(actor[1], 'decoratedPotShredNamesSize') is not None
    from .native_sign_data import TEMPLATES
    return material[0] in TEMPLATES and field_key(actor[1], 'signType') is not None


class _ContextWriter(object):
    """Resolve each prepared material's output buckets once per native batch."""
    def __init__(self, palette, native_render_profile=None):
        self.palette, self.cache = palette, {}
        self.native_render_profile = native_render_profile

    def put(self, rendered, index, delta):
        key = id(rendered)
        plan = self.cache.get(key)
        if plan is None:
            cell = rendered[0]
            layers = (('extra',) if independent_body(cell.get('common')) or
                      _native_actor_mesh(cell, self.native_render_profile)
                      else ('common', 'extra'))
            buckets = []
            for layer in layers:
                value = cell.get(layer)
                if value is not None and value != AIR:
                    buckets.append(self.palette[layer].setdefault(value, []))
            actor = None if layers == ('extra',) else cell.get('actor')
            if actor is not None:
                name, payload = actor
                actor = (self.palette['actor'].setdefault(name, {}), payload)
            # Retain the rendered object so its id cannot be reused in this cache.
            plan = (rendered, buckets, actor)
            self.cache[key] = plan
        for bucket in plan[1]:
            bucket.append(index)
        if plan[2] is not None:
            bucket, payload = plan[2]
            bucket[index] = rebase(payload, delta)


def prepare_context_palette(source, targets, render_origin=(0, 0, 0), item_profile=None):
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
    prepared = prepare_palette(source, render_origin=render_origin, item_profile=item_profile)
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
            _put(data, context_cell(cell), context_position(target, neighbor), original)
        body = cells[target_index].get('common')
        if independent_body(body):
            pos = (target[0], target[1] + OVERLAY_BASE, target[2])
            data['common'].setdefault(body, []).append(_index(pos, volume))
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
    def __init__(self, document, targets, render_origin=(0, 0, 0), item_profile=None,
                 native_render_profile=None, cauldron_profile=None, liquid_profile=None,
                 spawner_profile=None, portal_profile=None):
        self.document, self.targets = document, targets
        self.item_profile = item_profile
        self.native_render_profile = native_render_profile
        self.cauldron_profile = cauldron_profile
        self.liquid_profile = liquid_profile
        self.spawner_profile = spawner_profile
        self.portal_profile = portal_profile
        from .liquid_render_ownership import identity
        self.liquid_identity = identity(liquid_profile)
        self.render_origin = validate_render_origin(render_origin)
        sx, sy, sz = document.size
        self.logical_volume = (sz, sx, sy)
        if (tuple(targets.get('volume', ())) != self.logical_volume or
                not 0 < sy <= MAX_LOGICAL_HEIGHT):
            raise ValueError('Context palettes require matching supported logical volumes')
        self.cache, self.data = {}, None
        self.chest_identities = frozenset(identity for identity, value in enumerate(document.blocks.palette)
                                          if foreground(value)[0] in CHEST_PROXIES)
        self.position_identities = self.chest_identities | frozenset(
            identity for identity, value in enumerate(document.blocks.palette)
            if foreground(value)[0] == 'minecraft:bed' or
            position_sensitive(foreground(value), background(value)))
        self.states, self.extra_states = {}, {}
        self.chunk_cache = OrderedDict()
        self.positions = []

    def _chunk(self, key):
        entry = self.chunk_cache.get(key)
        if entry is None:
            chunk = self.document.blocks.chunks.get(key, 0)
            if not isinstance(chunk, integer_types):
                chunk = tuple(chunk)
                rendered_cells = [_NOT_RENDERED] * 4096
            elif not chunk:
                rendered_cells = None
            else:
                # Pair pose and bed color depend on each cell's logical neighbor.
                rendered_cells = [_NOT_RENDERED] * (4096 if chunk in self.position_identities else 1)
            # Bound expanded Python integers even for large sparse snapshots.
            if len(self.chunk_cache) == MAX_CONTEXT_CHUNK_CACHE:
                self.chunk_cache.popitem(last=False)
            entry = (chunk, rendered_cells)
            self.chunk_cache[key] = entry
        return entry

    def material(self, x, y, z):
        chunk, rendered_cells = self._chunk((x >> 4, y >> 4, z >> 4))
        if rendered_cells is None:
            return None
        index = ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)
        render_index = 0 if len(rendered_cells) == 1 else index
        result = rendered_cells[render_index]
        if result is not _NOT_RENDERED:
            return result
        identity = chunk if isinstance(chunk, integer_types) else chunk[index]
        if not identity:
            rendered_cells[render_index] = None
            return None
        if identity not in self.position_identities:
            cached = self.cache.get(identity)
            if cached is not None:
                rendered_cells[render_index] = cached
                return cached
        value = self.document.blocks.palette[identity]
        front, back, actor = foreground(value), background(value), actor_data(value)
        part = document_chest_part(self.document, (x, y, z), front)
        color = document_bed_color(self.document, (x, y, z), front) if front[0] == 'minecraft:bed' else None
        plant_position = ((x, y, z) if position_sensitive(front, back) else None)
        cache_key = (identity if part is None and color is None and plant_position is None else
                     (identity, part, color, plant_position))
        if cache_key in self.cache:
            result = self.cache[cache_key]
            rendered_cells[render_index] = result
            return result
        source = {'volume': (1, 1, 1), 'common': {}, 'extra': {}, 'actor': {}}
        if front != AIR:
            source['common'][front] = [0]
        if back != AIR:
            source['extra'][back] = [0]
        if actor is not None:
            source['actor'][front[0]] = {0: actor}
        rendered = prepare_palette(source, {(front[0], 0): part} if part is not None else None,
                                   inferred_bed_colors={0: color} if color is not None else None,
                                   render_origin=tuple(self.render_origin[i] + (x, y, z)[i] for i in range(3)),
                                   item_profile=self.item_profile,
                                   native_render_profile=self.native_render_profile,
                                   cauldron_profile=self.cauldron_profile, biome=self.document.biome,
                                   liquid_profile=self.liquid_profile, spawner_profile=self.spawner_profile,
                                   portal_profile=self.portal_profile)
        cells, overlays = _cells(rendered, (1, 1, 1))
        result = (cells.get(0), overlays.get(0), rendered['states'], rendered['extraStates'])
        self.cache[cache_key] = result
        rendered_cells[render_index] = result
        self.states.update(result[2])
        self.extra_states.update(result[3])
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
        if center is None:
            raise ValueError('Context target is absent from the complete source palette')
        if center[0] is None and center[1] is None:
            return
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
            _put_encoded(self.data, context_cell(rendered[0]), center_index + index_delta, delta)
        body = center[0].get('common') if center[0] is not None else None
        if independent_body(body):
            pos = (target[0], target[1] + OVERLAY_BASE, target[2])
            self.data['common'].setdefault(body, []).append(_index(pos, self.data['volume']))
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


def prepare_document_context(document, targets, render_origin=(0, 0, 0), item_profile=None):
    """Synchronously adapt a small palette without serializing the whole source."""
    builder = ContextPaletteBuilder(document, targets, render_origin=render_origin,
                                    item_profile=item_profile)
    for unused in builder.prepare():
        pass
    return builder.data


class ContextBatchBuilder(ContextPaletteBuilder):
    """Bound native input positions to 64 while preserving complete neighbors."""
    def prepare(self):
        for unused in self.collect():
            yield True
        batches = {}
        sx, sy, sz = self.document.size
        for number, target in enumerate(self.positions, 1):
            tx, ty, tz = target
            origin = (tx & ~15, ty & ~15, tz & ~15)
            batch = batches.get(origin)
            if batch is None:
                def palette(volume):
                    return {'volume': volume, 'common': {}, 'extra': {}, 'actor': {},
                            'states': {}, 'extraStates': {}, 'void': False, 'eliminateAir': True}
                context, overlay = palette((64, 64, 64)), palette((16, 16, 16))
                batch = (context, overlay, _ContextWriter(context, self.native_render_profile))
                batches[origin] = batch
            context, overlay, writer = batch
            center = self.material(*target)
            if center is None:
                raise ValueError('Context target is absent from its source')
            if center[0] is None and center[1] is None:
                if number % TARGETS_PER_UNIT == 0:
                    yield True
                continue
            lx, ly, lz = tx - origin[0], ty - origin[1], tz - origin[2]
            cx, cy, cz = (lx * CONTEXT_STRIDE + CONTEXT_CENTER,
                          ly * CONTEXT_STRIDE + CONTEXT_CENTER,
                          lz * CONTEXT_STRIDE + CONTEXT_CENTER)
            delta = (cx - tx, cy - ty, cz - tz)
            center_index = (cy * 64 + cx) * 64 + cz
            body = center[0].get('common') if center[0] is not None else None
            if independent_body(body):
                # A neighboring tile cannot distinguish ownership of a shared
                # boundary plane. Emit this body only in its target's local batch.
                overlay['common'].setdefault(body, []).append((ly * 16 + lx) * 16 + lz)
            if center[0] is not None and _native_actor_mesh(center[0], self.native_render_profile):
                # Native block actors carry a model-local POSITION. Their
                # model transform cannot use the packed neighbor-tile decoder.
                actor_cell = {'common': center[0].get('common'),
                              'actor': center[0].get('actor')}
                _put_encoded(overlay, actor_cell, (ly * 16 + lx) * 16 + lz,
                             tuple(-value for value in origin))
            for nx, ny, nz, index_delta in LOCAL_NEIGHBORS:
                x, y, z = tx + nx, ty + ny, tz + nz
                if not (0 <= x < sx and 0 <= y < sy and 0 <= z < sz):
                    continue
                rendered = center if nx == ny == nz == 0 else self.material(x, y, z)
                if rendered is None or rendered[0] is None:
                    continue
                writer.put(rendered, center_index + index_delta, delta)
            if center[1] is not None:
                overlay['common'].setdefault(center[1], []).append((ly * 16 + lx) * 16 + lz)
            if number % TARGETS_PER_UNIT == 0:
                yield True
        self.finish(batches)
        yield True

    def finish(self, batches):
        rows = []
        for origin, palettes in sorted(batches.items()):
            for kind, palette in enumerate(palettes[:2]):
                if not palette['common'] and not palette['extra']:
                    continue
                if self.native_render_profile is not None:
                    palette['_native_render_profile'] = profile_identity(self.native_render_profile)
                if self.cauldron_profile is not None:
                    palette['_cauldron_profile'] = self.cauldron_profile.identity
                if self.liquid_identity:
                    palette['_liquid_render_profile'] = self.liquid_identity
                if self.spawner_profile is not None:
                    palette['_spawner_profile'] = self.spawner_profile.identity
                if self.portal_profile is not None:
                    palette['_portal_profile'] = self.portal_profile.identity
                for key, layer, records in (('states', 'common', self.states),
                                             ('extraStates', 'extra', self.extra_states)):
                    palette[key] = dict((value, records[value]) for value in palette[layer]
                                        if value in records)
                if kind == 0 and palette['extra']:
                    # Splitting actor meshes can leave secondary layers without a foreground.
                    normalize_palette_layers(palette['common'], palette['states'],
                                             palette['extra'], palette['extraStates'])
                    for key, layer in (('states', 'common'), ('extraStates', 'extra')):
                        palette[key] = dict((value, record) for value, record in palette[key].items()
                                            if value in palette[layer])
                rows.append((origin, kind == 0, palette))
        from .render_layout import LOCAL_CONTEXT_SCHEMA_VERSION
        self.data = {'_context_batches': rows, '_context_schema': LOCAL_CONTEXT_SCHEMA_VERSION,
                     'volume': self.logical_volume}


def prepare_context_batches(document, targets, render_origin=(0, 0, 0), item_profile=None,
                            native_render_profile=None, cauldron_profile=None, liquid_profile=None,
                            spawner_profile=None, portal_profile=None):
    builder = ContextBatchBuilder(document, targets, render_origin=render_origin,
                                  item_profile=item_profile,
                                  native_render_profile=native_render_profile,
                                  cauldron_profile=cauldron_profile, liquid_profile=liquid_profile,
                                  spawner_profile=spawner_profile, portal_profile=portal_profile)
    for unused in builder.prepare():
        pass
    return builder.data


def has_native_draws(prepared):
    """Custom-owned cells can have logical targets without any native mesh."""
    if '_context_batches' in prepared:
        return bool(prepared['_context_batches'])
    return bool(prepared.get('common') or prepared.get('extra'))
