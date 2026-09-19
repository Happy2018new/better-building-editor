# -*- coding: utf-8 -*-
"""Coordinate input shared by real keyboard input and application validation."""
from __future__ import unicode_literals
import re

# The ModSDK Python 2.7 runtime omits unicodedata. Normalize the characters
# produced by Chinese keyboards without an unavailable C extension.
_FULLWIDTH = dict((ord(a), ord(b)) for a, b in zip('０１２３４５６７８９，＋－　', '0123456789,+- '))


def parse_coordinates(raw):
    if isinstance(raw, bytes):
        raw = raw.decode('utf8')
    raw = raw.translate(_FULLWIDTH).strip()
    # Chinese IMEs commonly produce full-width commas/digits. Also accept the
    # multiplication notation used to describe a document's dimensions.
    raw = raw.replace('、', ',').replace('×', ',').replace('*', ',').replace('x', ',').replace('X', ',')
    pieces = raw.split(',') if ',' in raw else raw.split()
    if len(pieces) != 3 or any(not re.match(r'^[+-]?\d+$', part.strip()) for part in pieces):
        raise ValueError('格式：X, Y, Z · 整数')
    return tuple(int(part.strip()) for part in pieces)
