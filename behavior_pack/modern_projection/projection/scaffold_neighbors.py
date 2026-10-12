"""Static scaffold support distances without falling or whole-chain selection."""
from collections import deque

from .cell import foreground
from .storage import Selection, address, CELLS
from . import block_registry as registry
from . import scaffold_support_data as source
from .scaffold_support_data import SUPPORTING_BLOCKS, SUPPORTING_AUX, NONSUPPORTING_AUX

HORIZONTAL = ((1, 0, 0), (-1, 0, 0), (0, 0, 1), (0, 0, -1))
VERTICAL = ((0, 1, 0), (0, -1, 0))


def _add(pos, offset):
    return tuple(pos[i] + offset[i] for i in range(3))


def support(value):
    native = registry.try_canonical(foreground(value))
    if native is None:
        return None
    name, aux = native
    if name == 'minecraft:air':
        return False
    if (getattr(source, 'SCHEMA_VERSION', None) != 1 or
            source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256.lower() != registry.fingerprint().lower()):
        raise ValueError('Native scaffold supports need regeneration for this block registry')
    if name in SUPPORTING_BLOCKS or aux in SUPPORTING_AUX.get(name, ()):
        return True
    if aux in NONSUPPORTING_AUX.get(name, ()):
        return False
    return None


def _is_scaffold(value, properties):
    state = properties(value)
    return 'stability' in state and 'stability_check' in state


def _component_steps(context, start, visited, properties, component):
    pending = deque((start,))
    visited.add(start)
    while pending:
        pos = pending.popleft()
        component.add(pos)
        for offset in HORIZONTAL + VERTICAL:
            target = _add(pos, offset)
            if target not in visited and _is_scaffold(context.get_cell(target), properties):
                visited.add(target)
                pending.append(target)
        yield None


def _distance(distances, pos):
    key, index = address(pos)
    chunk = distances.get(key)
    return chunk[index] if chunk is not None else 7


def _assign(distances, pos, value):
    key, index = address(pos)
    chunk = distances.get(key)
    if chunk is None:
        chunk = bytearray([7]) * CELLS
        distances[key] = chunk
    chunk[index] = value


def _distances_steps(context, component, properties, distances, frozen):
    queues = [deque() for unused in range(7)]
    for pos in component:
        value = context.get_cell(pos)
        below = _add(pos, (0, -1, 0))
        capability = None if below in component else support(context.get_cell(below))
        if not context.can_change(pos) or pos in context.preserve or capability is None and below not in component:
            frozen.add(pos)
            distance = properties(value)['stability']
        else:
            distance = 0 if capability else 7
        if distance < 7:
            _assign(distances, pos, distance)
            queues[distance].append(pos)
        yield None
    # Vertical support travels upward for free; each horizontal edge costs one.
    for distance, pending in enumerate(queues):
        while pending:
            pos = pending.popleft()
            if _distance(distances, pos) != distance:
                continue
            for offset in HORIZONTAL + ((0, 1, 0),):
                target = _add(pos, offset)
                desired = distance + (0 if offset[1] else 1)
                if target in component and target not in frozen and desired < _distance(distances, target):
                    _assign(distances, target, desired)
                    queues[desired].append(target)
            yield None


def reconcile_steps(context, candidates, properties, with_properties):
    """Update entire affected components within the initiating edit transaction."""
    visited = Selection()
    for start in candidates:
        if start in visited or not _is_scaffold(context.get_cell(start), properties):
            continue
        component = Selection()
        for unused in _component_steps(context, start, visited, properties, component):
            yield None
        distances, frozen = {}, Selection()
        for unused in _distances_steps(context, component, properties, distances, frozen):
            yield None
        for pos in component:
            if pos not in frozen:
                value = context.get_cell(pos)
                updated = with_properties(value, {'stability': _distance(distances, pos)})
                if updated != value:
                    context.write(pos, updated)
            yield None
