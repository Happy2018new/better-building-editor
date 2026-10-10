"""Prepare one missing-only mesh while retaining each cell's native neighbors."""
from .cell import AIR
from .geometry_palette import prepare_palette
from .large_preview import MAX_SURFACE_BLOCKS
from .nbt_spatial import rebase
from .render_layout import (CONTEXT_BASE, CONTEXT_STRIDE, MAX_LOGICAL_HEIGHT,
                            OVERLAY_BASE, context_position)

NEIGHBORS = tuple((x, y, z) for y in (-1, 0, 1)
                  for x in (-1, 0, 1) for z in (-1, 0, 1))


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
    for layer in ('common', 'extra'):
        value = cell.get(layer)
        if value is not None and value != AIR:
            data[layer].setdefault(value, []).append(index)
    actor = cell.get('actor')
    if actor is not None:
        name, payload = actor
        delta = tuple(position[axis] - original[axis] for axis in range(3))
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
