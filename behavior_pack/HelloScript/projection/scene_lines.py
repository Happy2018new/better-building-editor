"""Camera-space overlay geometry, shared by the native scene and tests."""


def cuboid(lo, hi):
    for axis in range(3):
        other = [i for i in range(3) if i != axis]
        for corner in range(4):
            a = list(lo)
            a[other[0]] = (lo, hi)[corner // 2][other[0]]
            a[other[1]] = (lo, hi)[corner % 2][other[1]]
            b = list(a); b[axis] = hi[axis]
            yield tuple(a), tuple(b)


def grid_lines(origin, size, layer):
    if not origin[1] <= layer < origin[1] + size[1]:
        return []
    result = []
    for axis in (0, 2):
        other = 2 if axis == 0 else 0
        start, end = origin[axis], origin[axis] + size[axis]
        for value in range(start, end+1):
            a = list(origin); a[1] = layer; a[axis] = value
            b = list(a); b[other] += size[other]
            result.append((tuple(a), tuple(b)))
    return result


def clip_line(a, b, width, height):
    dx, dy = b[0] - a[0], b[1] - a[1]
    low, high = 0., 1.
    for p, q in ((-dx, a[0]), (dx, width - a[0]), (-dy, a[1]), (dy, height - a[1])):
        if abs(p) < 1e-9:
            if q < 0:
                return None
        elif p < 0:
            low = max(low, q / p)
        else:
            high = min(high, q / p)
    if low > high:
        return None
    return ((a[0] + low * dx, a[1] + low * dy), (a[0] + high * dx, a[1] + high * dy))


def clip_depth(a, b, plane):
    """Clip a world-space overlay segment at the same near plane as picking."""
    if plane is None:
        return a,b
    da=sum(a[i]*plane[0][i] for i in range(3))-plane[1]
    db=sum(b[i]*plane[0][i] for i in range(3))-plane[1]
    if da>0 and db>0:
        return None
    if (da>0) != (db>0):
        point=tuple(a[i]+(b[i]-a[i])*da/(da-db) for i in range(3))
        return (point,b) if da>0 else (a,point)
    return a,b
