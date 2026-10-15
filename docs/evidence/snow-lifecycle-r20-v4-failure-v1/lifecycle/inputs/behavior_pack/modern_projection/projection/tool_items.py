# -*- coding: utf-8 -*-
"""Small, shared rules for craftable world tools."""
from __future__ import unicode_literals
from .model import Document

SURVEY_WAND = 'modern_projection:survey_wand'
TERMINAL = 'modern_projection:terminal'


def item_name(item):
    if not isinstance(item, dict):
        return None
    name = item.get('newItemName') or item.get('itemName')
    if isinstance(name, bytes):
        return name.decode('utf8')
    return name


def selection(first, second):
    if len(first) != 3 or len(second) != 3:
        raise ValueError('选点坐标无效')
    if any(type(value) is not int for value in tuple(first) + tuple(second)):
        raise ValueError('选点坐标无效')
    origin = tuple(min(first[i], second[i]) for i in range(3))
    size = tuple(abs(first[i] - second[i]) + 1 for i in range(3))
    Document(size)
    return origin, size


def unique_name(origin, names):
    base = '世界选区 %d,%d,%d' % tuple(origin)
    used = set(names)
    if base not in used:
        return base
    for index in range(2, 10000):
        candidate = '%s (%d)' % (base, index)
        if candidate not in used:
            return candidate
    raise ValueError('同名世界选区太多，请整理建筑库')
