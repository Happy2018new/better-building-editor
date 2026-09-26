# -*- coding: utf-8 -*-
"""Shared document-space bounds for 16-cubed editing and native palettes."""
EDGE = 16


def tile_bounds(size, key):
    origin = tuple(v * EDGE for v in key)
    extent = tuple(min(EDGE, size[i] - origin[i]) for i in range(3))
    return origin, extent


def view_bounds(size, focus=None):
    if focus is None:
        return (0, 0, 0), size
    key = tuple(max(0, min(size[i]-1, int(focus[i]))) // EDGE for i in range(3))
    return tile_bounds(size, key)


def keys_in(origin, size):
    return tuple((x, y, z)
                 for x in range(origin[0]//EDGE, (origin[0]+size[0]-1)//EDGE+1)
                 for y in range(origin[1]//EDGE, (origin[1]+size[1]-1)//EDGE+1)
                 for z in range(origin[2]//EDGE, (origin[2]+size[2]-1)//EDGE+1))


def painter_order(keys, toward):
    """Stable back-to-front order for disjoint, axis-aligned cells.

    A ray traverses cell indices monotonically on every axis. Signed
    lexicographic order therefore respects every overlapping pair, without
    reordering unrelated cells as their centre depths cross during orbit.
    """
    signs = tuple(1 if value >= 0 else -1 for value in toward)
    ordered = sorted(keys, key=lambda key: tuple(key[i]*signs[i] for i in range(3)))
    return dict((key, rank) for rank, key in enumerate(ordered))
