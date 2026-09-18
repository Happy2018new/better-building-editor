# -*- coding: utf-8 -*-
"""Bounded overview and precise local previews, built in resumable steps."""
from __future__ import unicode_literals
from collections import Counter
from .model import AIR, Document
from .storage import integer_types, position


def build_preview(document, hidden=(), layer=None, focus=None):
    hidden = set(hidden)
    if focus is not None:
        size = tuple(min(32, v) for v in document.size)
        origin = tuple(max(0, min(document.size[i] - size[i], focus[i] - size[i] // 2)) for i in range(3))
        out = Document(size)
        for y in range(size[1]):
            if origin[1] + y in hidden or (layer is not None and origin[1] + y != layer):
                continue
            for z in range(size[2]):
                for x in range(size[0]):
                    value = document.get((origin[0] + x, origin[1] + y, origin[2] + z))
                    if value != AIR:
                        out.blocks[(x, y, z)] = value
                yield None
        yield out, origin, 1
        return
    out = Document(tuple((v + 15) // 16 for v in document.size))
    for key in sorted(document.blocks.chunks):
        chunk = document.blocks.chunks[key]
        ys = [y for y in range(16) if (key[1] * 16 + y) not in hidden and
              (layer is None or key[1] * 16 + y == layer)]
        if ys:
            if isinstance(chunk, integer_types):
                identity = chunk
            else:
                counts = Counter(v for y in ys for v in chunk[y * 256:(y + 1) * 256] if v)
                identity = counts.most_common(1)[0][0] if counts else 0
            if identity:
                out.blocks[key] = document.blocks.palette[identity]
        yield None
    yield out, (0, 0, 0), 16
