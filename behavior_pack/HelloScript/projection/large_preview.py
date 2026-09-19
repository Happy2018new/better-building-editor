# -*- coding: utf-8 -*-
"""Exact surface palettes. Chunking schedules work; it never rescales voxels."""
from __future__ import unicode_literals
from .storage import integer_types
from .camera import behind_plane
from .chunks import view_bounds

# Unknown/custom/transparent/non-cubic blocks never conceal their neighbours.
OPAQUE = frozenset('stone stonebrick planks concrete wool quartz_block dirt grass '
                   'cobblestone brick_block sandstone sea_lantern bedrock sand gravel '
                   'gold_block iron_block diamond_block emerald_block obsidian'.split())
MAX_SURFACE_BLOCKS = 750000


class SurfacePalette(object):
    def __init__(self, size):
        self.size = size
        self.common = {}
        self.count = 0

    def add(self, pos, value):
        self.count += 1
        if self.count > MAX_SURFACE_BLOCKS:
            raise ValueError('可见方块数量过多，请使用精细视图或仅显示当前层；草稿完整保留')
        x, y, z = pos
        self.common.setdefault(value, []).append(y * self.size[0] * self.size[2] + x * self.size[2] + z)

    def palette_data(self, visible=None):
        sx, sy, sz = self.size
        return {'extra': {}, 'actor': {}, 'void': False, 'volume': (sz, sx, sy),
                'common': self.common, 'eliminateAir': True}


def build_preview(document, hidden=(), layer=None, focus=None, plane=None, region=None, local=False):
    hidden = set(hidden)
    origin, size = view_bounds(document.size, focus)
    end = tuple(origin[i] + size[i] for i in range(3))
    scan_lo = origin if region is None else tuple(max(origin[i], region[0][i]) for i in range(3))
    scan_hi = end if region is None else tuple(min(end[i], region[1][i]) for i in range(3))
    palette_origin = scan_lo if local else origin
    out = SurfacePalette(tuple(scan_hi[i]-scan_lo[i] for i in range(3)) if local else size)
    store = document.blocks
    opaque = [value[0].startswith('minecraft:') and value[0].split(':')[-1] in OPAQUE for value in store.palette]
    ys = set(y for y in range(origin[1], end[1]) if y not in hidden and (layer is None or y == layer))

    def conceals(x, y, z):
        if not (origin[0] <= x < end[0] and origin[2] <= z < end[2] and y in ys):
            return False
        if not behind_plane((x, y, z), plane):
            return False
        chunk = store.chunks.get((x >> 4, y >> 4, z >> 4), 0)
        value = chunk if isinstance(chunk, integer_types) else chunk[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]
        return opaque[value]

    for key in sorted(store.chunks):
        base = tuple(v * 16 for v in key)
        if any(base[i] >= scan_hi[i] or base[i] + 16 <= scan_lo[i] for i in range(3)):
            continue
        uncut = True
        fully_visible = True
        if plane is not None:
            near = tuple(base[i] + (0 if plane[0][i] >= 0 else 15) for i in range(3))
            last = tuple(base[i] + (15 if plane[0][i] >= 0 else 0) for i in range(3))
            far = tuple(base[i] + (16 if plane[0][i] >= 0 else -1) for i in range(3))
            if not behind_plane(near, plane):
                yield None
                continue
            uncut = behind_plane(far, plane)
            fully_visible = behind_plane(last, plane)
        chunk = store.chunks[key]
        uniform = isinstance(chunk, integer_types)
        enclosed = (uncut and uniform and opaque[chunk] and
                    all(origin[i] < base[i] and base[i] + 16 < end[i] for i in (0, 2)) and
                    all(base[1] + y in ys for y in range(-1, 17)))
        if enclosed:
            for axis in range(3):
                for delta in (-1, 1):
                    neighbour = list(key); neighbour[axis] += delta
                    other = store.chunks.get(tuple(neighbour), 0)
                    if not isinstance(other, integer_types) or not opaque[other]:
                        enclosed = False
        if enclosed:
            yield None
            continue
        if fully_visible and uniform and opaque[chunk]:
            low = tuple(max(base[i], scan_lo[i]) for i in range(3))
            high = tuple(min(base[i] + 16, scan_hi[i]) - 1 for i in range(3))
            def blocked(axis, delta):
                edge = low[axis] if delta < 0 else high[axis]
                if (delta < 0 and edge == origin[axis]) or (delta > 0 and edge == end[axis]-1):
                    return False
                if not uncut:
                    # A full chunk may border a clipped neighbour. Include that
                    # face, then test its voxels, without scanning the interior.
                    face = [high[i] if plane[0][i] >= 0 else low[i] for i in range(3)]
                    face[axis] = edge + delta
                    if not behind_plane(face, plane):
                        return False
                if base[axis] < edge + delta < base[axis] + 16:
                    return True
                neighbour = list(key); neighbour[axis] += delta
                other = store.chunks.get(tuple(neighbour), 0)
                return isinstance(other, integer_types) and opaque[other]
            xs = [edge for delta, edge in ((-1, low[0]), (1, high[0])) if not blocked(0, delta)]
            zs = [edge for delta, edge in ((-1, low[2]), (1, high[2])) if not blocked(2, delta)]
            bottom, top = blocked(1, -1), blocked(1, 1)
            simple = uncut
            for axis in range(3):
                for delta in (-1, 1):
                    neighbour = list(key); neighbour[axis] += delta
                    if not isinstance(store.chunks.get(tuple(neighbour), 0), integer_types):
                        simple = False
            for y in range(low[1], high[1]+1):
                if y not in ys:
                    continue
                exposed_layer = y-1 not in ys or y+1 not in ys or (y == low[1] and not bottom) or (y == high[1] and not top)
                for z in range(low[2], high[2]+1):
                    for x in (range(low[0], high[0]+1) if exposed_layer or z in zs else xs):
                        if simple or not (conceals(x-1, y, z) and conceals(x+1, y, z) and conceals(x, y-1, z) and
                                conceals(x, y+1, z) and conceals(x, y, z-1) and conceals(x, y, z+1)):
                            out.add((x-palette_origin[0], y-palette_origin[1], z-palette_origin[2]), store.palette[chunk])
                    yield None
            continue
        for y in range(max(base[1], scan_lo[1]), min(base[1] + 16, scan_hi[1])):
            if y not in ys:
                continue
            for z in range(max(base[2], scan_lo[2]), min(base[2] + 16, scan_hi[2])):
                for x in range(max(base[0], scan_lo[0]), min(base[0] + 16, scan_hi[0])):
                    identity = chunk if uniform else chunk[((y & 15) << 8) | ((z & 15) << 4) | (x & 15)]
                    if not identity:
                        continue
                    if not behind_plane((x, y, z), plane):
                        continue
                    interior = (uncut and uniform and opaque[identity] and base[0] < x < base[0] + 15 and
                                base[2] < z < base[2] + 15 and base[1] < y < base[1] + 15 and
                                origin[0] < x < end[0] - 1 and origin[2] < z < end[2] - 1 and y-1 in ys and y+1 in ys)
                    if interior or (conceals(x-1, y, z) and conceals(x+1, y, z) and conceals(x, y-1, z) and
                                    conceals(x, y+1, z) and conceals(x, y, z-1) and conceals(x, y, z+1)):
                        continue
                    out.add((x-palette_origin[0], y-palette_origin[1], z-palette_origin[2]), store.palette[identity])
                yield None
    yield out, palette_origin, 1
