# -*- coding: utf-8 -*-
"""Join native geometry regions wherever a tile boundary cuts a neighbour shape."""
from .chunks import EDGE, keys_in
from .block_traits import is_solid
from .storage import integer_types


def _identity(chunk, x, y, z):
    return chunk if isinstance(chunk, integer_types) else chunk[(y << 8) | (z << 4) | x]


def _boundary_depends(document, key, other, axis, opaque):
    store = document.blocks
    left, right = store.chunks.get(key, 0), store.chunks.get(other, 0)
    if not left or not right:
        return False
    if isinstance(left, integer_types) and isinstance(right, integer_types):
        return not (opaque[left] and opaque[right])
    across = tuple(i for i in range(3) if i != axis)
    extent = tuple(min(EDGE, document.size[i] - key[i] * EDGE) for i in range(3))
    for a in range(extent[across[0]]):
        for b in range(extent[across[1]]):
            point = [0, 0, 0]
            point[axis] = EDGE - 1
            point[across[0]], point[across[1]] = a, b
            first = _identity(left, *point)
            point[axis] = 0
            second = _identity(right, *point)
            if first and second and not (opaque[first] and opaque[second]):
                return True
    return False


def regions(document):
    """Partition the document into disjoint rectangular native palettes.

    Every unknown, custom or non-full block is conservative: if it meets a
    neighbour across a tile boundary, both tiles share native shape context.
    Rectangle closure also absorbs empty tiles so overlapping group bounds
    can never draw another region's cells twice.
    """
    keys = keys_in((0, 0, 0), document.size)
    parent = dict((key, key) for key in keys)
    opaque = tuple(is_solid(value) for value in document.blocks.palette)

    def owner(key):
        while parent[key] != key:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    def join(left, right):
        first, second = owner(left), owner(right)
        if first == second:
            return False
        parent[max(first, second)] = min(first, second)
        return True

    for key in keys:
        for axis in range(3):
            other = tuple(key[i] + (1 if i == axis else 0) for i in range(3))
            if other in parent and _boundary_depends(document, key, other, axis, opaque):
                join(key, other)

    changed = True
    while changed:
        changed = False
        groups = {}
        for key in keys:
            groups.setdefault(owner(key), []).append(key)
        for root, members in groups.items():
            low = tuple(min(key[i] for key in members) for i in range(3))
            high = tuple(max(key[i] for key in members) for i in range(3))
            for key in keys:
                if all(low[i] <= key[i] <= high[i] for i in range(3)):
                    changed = join(root, key) or changed

    groups = {}
    for key in keys:
        groups.setdefault(owner(key), []).append(key)
    output = {}
    for root, members in groups.items():
        low = tuple(min(key[i] for key in members) * EDGE for i in range(3))
        high = tuple(min(document.size[i], (max(key[i] for key in members) + 1) * EDGE)
                     for i in range(3))
        entry = (root, low, high, tuple(sorted(members)))
        for key in members:
            output[key] = entry
    return output
