# -*- coding: utf-8 -*-
"""Compact 16-cubed storage and selections, compatible with Python 2.7.

Uniform chunks cost one palette id. Mixed chunks use 8192 bytes. Copies share
chunks until the first write, so an atomic edit and its undo need no cell dicts.
"""
from __future__ import unicode_literals
from array import array
from collections import Counter

AIR = ('minecraft:air', 0)
EDGE = 16
CELLS = 4096
FULL = (1 << CELLS) - 1
try:
    integer_types = (int, long)
    range_iter = xrange
except NameError:
    integer_types = (int,)
    range_iter = range


def address(pos):
    x, y, z = pos
    return (x >> 4, y >> 4, z >> 4), ((y & 15) << 8) | ((z & 15) << 4) | (x & 15)


def position(key, index):
    return ((key[0] << 4) + (index & 15), (key[1] << 4) + (index >> 8),
            (key[2] << 4) + ((index >> 4) & 15))


def indices(mask):
    if mask == FULL:
        for index in range_iter(CELLS):
            yield index
    else:
        while mask:
            bit = mask & -mask
            yield bit.bit_length() - 1
            mask ^= bit


class Selection(object):
    """One bit per selected cell; full cuboids never allocate coordinate tuples."""
    def __init__(self, points=()):
        self.chunks = {}
        self.count = 0
        self._bounds = None
        for point in points:
            self.add(point)

    @classmethod
    def box(cls, lo, hi):
        out = cls()
        if any(lo[i] > hi[i] for i in range(3)):
            return out
        for cy in range_iter(lo[1] >> 4, (hi[1] >> 4) + 1):
            for cz in range_iter(lo[2] >> 4, (hi[2] >> 4) + 1):
                for cx in range_iter(lo[0] >> 4, (hi[0] >> 4) + 1):
                    key = (cx, cy, cz)
                    a = [max(0, lo[i] - (key[i] << 4)) for i in range(3)]
                    b = [min(15, hi[i] - (key[i] << 4)) for i in range(3)]
                    if a == [0, 0, 0] and b == [15, 15, 15]:
                        mask = FULL
                    else:
                        row = ((1 << (b[0] - a[0] + 1)) - 1) << a[0]
                        plane = sum(row << (z * 16) for z in range(a[2], b[2] + 1))
                        mask = sum(plane << (y * 256) for y in range(a[1], b[1] + 1))
                    out.chunks[key] = mask
                    out.count += (b[0] - a[0] + 1) * (b[1] - a[1] + 1) * (b[2] - a[2] + 1)
        out._bounds = (tuple(lo), tuple(hi))
        return out

    def copy(self):
        out = Selection()
        out.chunks, out.count, out._bounds = dict(self.chunks), self.count, self._bounds
        return out

    def add(self, pos):
        key, index = address(pos)
        mask = self.chunks.get(key, 0)
        bit = 1 << index
        if not mask & bit:
            self.chunks[key] = mask | bit
            self.count += 1
            self._bounds = None

    def __len__(self):
        return self.count

    def __contains__(self, pos):
        key, index = address(pos)
        return bool(self.chunks.get(key, 0) & (1 << index))

    def __iter__(self):
        for key in sorted(self.chunks):
            for index in indices(self.chunks[key]):
                yield position(key, index)

    def __eq__(self, other):
        if isinstance(other, Selection):
            return self.chunks == other.chunks
        return len(self) == len(other) and all(p in other for p in self)

    def __ne__(self, other):
        return not self == other

    def bounds(self):
        if not self:
            raise ValueError('选区为空，请先选择方块')
        if self._bounds is None:
            low, high = [1 << 30] * 3, [-1] * 3
            x_masks = [sum(1 << (y * 256 + z * 16 + x) for y in range(16) for z in range(16)) for x in range(16)]
            z_masks = [sum(65535 << (y * 256 + z * 16) for y in range(16)) for z in range(16)]
            for key, mask in self.chunks.items():
                a = [(mask & -mask).bit_length() - 1, mask.bit_length() - 1]
                ys = (a[0] >> 8, a[1] >> 8)
                xs = [i for i in range(16) if mask & x_masks[i]]
                zs = [i for i in range(16) if mask & z_masks[i]]
                for axis, pair in enumerate(((xs[0], xs[-1]), ys, (zs[0], zs[-1]))):
                    low[axis] = min(low[axis], (key[axis] << 4) + pair[0])
                    high[axis] = max(high[axis], (key[axis] << 4) + pair[1])
            self._bounds = (tuple(low), tuple(high))
        return self._bounds

    def difference(self, other):
        if not isinstance(other, Selection):
            other = Selection(other)
        out = Selection()
        for key, mask in self.chunks.items():
            value = mask & ~other.chunks.get(key, 0)
            if value:
                out.chunks[key] = value
                out.count += bin(value).count('1')
        return out


class BlockStore(object):
    def __init__(self):
        self.chunks = {}
        self.palette = [AIR]
        self.palette_ids = {AIR: 0}
        self.owned = set()
        self.count = 0
        self.counts = Counter()
        self.layers = Counter()

    def copy(self):
        out = BlockStore()
        out.chunks = dict(self.chunks)
        out.palette, out.palette_ids = list(self.palette), dict(self.palette_ids)
        out.count, out.counts, out.layers = self.count, self.counts.copy(), self.layers.copy()
        # All existing arrays now have at least two owners. Each branch copies
        # only the chunks it subsequently modifies.
        self.owned.clear()
        return out

    def palette_id(self, value):
        found = self.palette_ids.get(value)
        if found is None:
            if len(self.palette) >= 65536:
                raise ValueError('建筑材质种类超过 65535')
            found = len(self.palette)
            self.palette.append(value)
            self.palette_ids[value] = found
        return found

    def __len__(self):
        return self.count

    def get(self, pos, default=None):
        key, index = address(pos)
        chunk = self.chunks.get(key, 0)
        identity = chunk if isinstance(chunk, integer_types) else chunk[index]
        return self.palette[identity] if identity else default

    def __getitem__(self, pos):
        value = self.get(pos)
        if value is None:
            raise KeyError(pos)
        return value

    def __contains__(self, pos):
        return self.get(pos) is not None

    def __setitem__(self, pos, value):
        key, index = address(pos)
        chunk = self.chunks.get(key, 0)
        old_id = chunk if isinstance(chunk, integer_types) else chunk[index]
        new_id = self.palette_id(value)
        if old_id == new_id:
            return
        if isinstance(chunk, integer_types):
            chunk = array('H', [chunk]) * CELLS
            self.chunks[key] = chunk
            self.owned.add(key)
        elif key not in self.owned:
            chunk = array('H', chunk)
            self.chunks[key] = chunk
            self.owned.add(key)
        chunk[index] = new_id
        delta = int(bool(new_id)) - int(bool(old_id))
        self.count += delta
        self.layers[pos[1]] += delta
        if old_id:
            self.counts[self.palette[old_id]] -= 1
        if new_id:
            self.counts[value] += 1

    def pop(self, pos, default=None):
        old = self.get(pos, default)
        if old is not default:
            self[pos] = AIR
        return old

    def items(self):
        for key in sorted(self.chunks):
            chunk = self.chunks[key]
            if isinstance(chunk, integer_types):
                if chunk:
                    value = self.palette[chunk]
                    for index in range_iter(CELLS):
                        yield position(key, index), value
            else:
                for index, identity in enumerate(chunk):
                    if identity:
                        yield position(key, index), self.palette[identity]

    iteritems = items

    def __iter__(self):
        for pos, unused in self.items():
            yield pos

    def keys(self):
        return iter(self)

    def values(self):
        for unused, value in self.items():
            yield value

    def __eq__(self, other):
        if not hasattr(other, 'get') or len(self) != len(other):
            return False
        if isinstance(other, BlockStore) and self.palette == other.palette and self.chunks == other.chunks:
            return True
        return all(other.get(p) == v for p, v in self.items())

    def __ne__(self, other):
        return not self == other

    def fill_chunk(self, key, value):
        """Full interior chunk only. Update statistics without expanding tuples."""
        identity = self.palette_id(value)
        old = self.chunks.get(key, 0)
        if isinstance(old, integer_types) and old == identity:
            return 0
        if isinstance(old, integer_types):
            counts = {old: CELLS}
            layers = [256 if old else 0] * 16
            changed = CELLS
        else:
            counts = Counter(old)
            layers = [sum(bool(v) for v in old[y * 256:(y + 1) * 256]) for y in range(16)]
            changed = CELLS - counts.get(identity, 0)
        old_count = CELLS - counts.get(0, 0)
        self.count += (CELLS if identity else 0) - old_count
        for previous, count in counts.items():
            if previous:
                self.counts[self.palette[previous]] -= count
        if identity:
            self.chunks[key] = identity
            self.counts[value] += CELLS
        else:
            self.chunks.pop(key, None)
        self.owned.discard(key)
        for y in range(16):
            self.layers[(key[1] << 4) + y] += (256 if identity else 0) - layers[y]
        return changed

    def memory_bytes(self):
        return len(self.chunks) * 128 + sum(CELLS * 2 for c in self.chunks.values() if not isinstance(c, integer_types))

    def compact(self, key):
        chunk = self.chunks.get(key, 0)
        if not isinstance(chunk, integer_types) and all(v == chunk[0] for v in chunk):
            if chunk[0]:
                self.chunks[key] = chunk[0]
            else:
                self.chunks.pop(key, None)
            self.owned.discard(key)
