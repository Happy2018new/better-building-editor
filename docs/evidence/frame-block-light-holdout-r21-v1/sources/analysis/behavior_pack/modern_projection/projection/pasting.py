# -*- coding: utf-8 -*-
"""Clipboard extent is independent of the current editing selection."""
from __future__ import unicode_literals


def paste_bounds(clipboard, origin):
    if not clipboard:
        return None
    return tuple(origin), tuple(origin[i]+clipboard['size'][i]-1 for i in range(3))


def paste_error(document, clipboard, origin):
    extent = paste_bounds(clipboard, origin)
    if extent is None:
        return '请先复制一个选区'
    if not document.contains(extent[0]) or not document.contains(extent[1]):
        return '粘贴范围超出建筑边界，请移动起点'
    return None
