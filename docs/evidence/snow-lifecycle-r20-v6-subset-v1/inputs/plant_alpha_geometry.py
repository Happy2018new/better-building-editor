"""Derive one planar alpha footprint from coincident signed-UV model faces."""


def face_alpha_spans(texture, face, reverse_winding=False):
    if set(face) != {'uv', 'uv_size'}:
        raise ValueError('Plant alpha oracle requires unrotated explicit face UVs')
    ux, vy = face['uv']
    du, dv = face['uv_size']
    if not du or not dv:
        raise ValueError('Plant alpha face has a zero UV dimension')
    min_u, max_u = sorted((ux, ux+du))
    min_v, max_v = sorted((vy, vy+dv))
    if not (0 <= min_u < max_u <= texture.width and
            0 <= min_v < max_v <= texture.height):
        raise ValueError('Plant alpha face UV extends outside the source texture')
    spans = set()
    for row in range(texture.height):
        low_v, high_v = max(row, min_v), min(row+1, max_v)
        if high_v <= low_v:
            continue
        y0, y1 = sorted((1.-(low_v-vy)/dv, 1.-(high_v-vy)/dv))
        for column in range(texture.width):
            if texture.getpixel((column, row))[3] <= 127:
                continue
            low_u, high_u = max(column, min_u), min(column+1, max_u)
            if high_u <= low_u:
                continue
            u0, u1 = sorted(((low_u-ux)/du, (high_u-ux)/du))
            if reverse_winding:
                u0, u1 = 1.-u1, 1.-u0
            spans.add(tuple(round(value, 12) for value in (u0, u1, y0, y1)))
    return spans


def planar_alpha_spans(cube, texture):
    """Return unit-plane opaque rectangles without inspecting rendered pixels.

    South's face winding runs opposite north's. A signed mirrored south UV
    therefore yields the same physical alpha footprint, not a second image.
    Different footprints require a camera-side oracle and cannot be unioned.
    """
    if cube['size'][2] != 0:
        raise ValueError('Plant alpha oracle requires zero-thickness crossed planes')
    uv = cube.get('uv', {})
    if set(uv) != {'north', 'south'}:
        raise ValueError('Plant alpha oracle requires explicit north/south UV faces')
    if texture.mode != 'RGBA':
        raise ValueError('Plant alpha oracle requires an RGBA source texture')
    front = face_alpha_spans(texture, uv['north'])
    back = face_alpha_spans(texture, uv['south'], reverse_winding=True)
    if front != back:
        raise ValueError('Plant front/back UV alpha differs; camera-side projection is required')
    return tuple(sorted(front))
