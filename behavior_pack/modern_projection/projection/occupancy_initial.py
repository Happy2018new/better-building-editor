"""Build initial occupancy palettes by chunk, with uniform-row fast paths."""
from .storage import integer_types


def prepare_chunk(tracker, store, key, size, output):
    t = tracker
    start = tuple(v*16 for v in key)
    sx, sy, sz = t.size
    chunk = store.chunks[key]
    uniform = isinstance(chunk, integer_types)
    cells = None if uniform else tuple(chunk)
    t.bulk.begin(key)
    sample = t.bulk.initial
    states = sample[1][0] if sample is not None else None
    homogeneous = (states[0] if states and states[0] and
                   states == bytearray([states[0]])*len(states) else 0)
    common = t.cached.setdefault(key, {})
    mask, count = 0, 0
    plane = sum(((1 << size[0])-1) << (z*16) for z in range(size[2]))
    for y in range(size[1]):
        if not t.visible_layer(start[1]+y):
            continue
        if uniform and homogeneous:
            # Native and Python buffers both accept contiguous row slices.
            # A solid 16^3 chunk needs 256 row operations, not 4096 lookups.
            mask |= plane << (y*256)
            count += size[0]*size[2]
            indices = common.setdefault(store.palette[chunk], [])
            for x in range(size[0]):
                first = ((start[1]+y)*sx+start[0]+x)*sz+start[2]
                end = first+size[2]
                t.state[first:end] = bytearray([homogeneous])*size[2]
                if homogeneous == 1:
                    t.slots[first:end] = range(len(indices), len(indices)+size[2])
                    indices.extend(range(first, end))
            yield True
            continue
        for z in range(size[2]):
            row = 0
            for x in range(size[0]):
                identity = chunk if uniform else cells[(y << 8) | (z << 4) | x]
                if not identity:
                    continue
                row |= 1 << x
                count += 1
                pos = (start[0]+x, start[1]+y, start[2]+z)
                index = (pos[1]*sx+pos[0])*sz+pos[2]
                state = states[(y*size[0]+x)*size[2]+z] if states is not None else 0
                if state:
                    t.state[index] = state
                    visible = state != 2
                else:
                    visible = t.read(pos, True)
                if visible:
                    indices = common.setdefault(store.palette[identity], [])
                    t.slots[index] = len(indices)
                    indices.append(index)
            mask |= row << (y*256+z*16)
        yield True
    if mask:
        t.targets.chunks[key] = mask
        t.targets.count += count
    for value, indices in common.items():
        if indices:
            output.common.setdefault(value, []).extend(indices)
            output.count += len(indices)
