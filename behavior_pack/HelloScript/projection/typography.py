# -*- coding: utf-8 -*-
"""Shared glyph metrics and punctuation-aware wrapping for all static UI text."""
from __future__ import unicode_literals
import sys
from .type_assets import ASSETS
from .font_atlas import GLYPHS

CLOSING = frozenset('，。！？；：、）》】」』…,.!?;:%）')
OPENING = frozenset('（《【「『(')
try:
    codepoint = unichr
except NameError:
    codepoint = chr


def characters(value):
    """Preserve supplementary glyphs on the game's narrow Python 2 unicode."""
    index = 0
    while index < len(value):
        char = value[index]
        index += 1
        if 0xd800 <= ord(char) <= 0xdbff and index < len(value) and 0xdc00 <= ord(value[index]) <= 0xdfff:
            char = (char+value[index] if sys.maxunicode <= 0xffff else
                    codepoint(0x10000 + ((ord(char)-0xd800)<<10) + ord(value[index])-0xdc00))
            index += 1
        yield char


def glyph(value):
    data = GLYPHS.get(value)
    if data is not None:
        page, x, y, width, advance = data
        return ('atlas_%03d' % page, width/64., 88/64., advance/64., (x,y), (width,88))
    data = ASSETS.get(value)
    return tuple(data[:4])+(tuple(data[4]),tuple(data[5])) if data is not None else None


def supported(value):
    return all(char == '\n' or char in GLYPHS or char in ASSETS for char in characters(value))


def layout(value, font, width=None, max_lines=None):
    """Return (glyph, row, x) and row widths; keep punctuation with its word."""
    lines=[[]];widths=[0.]
    for char in characters(value):
        if char == '\n':
            lines.append([]);widths.append(0.)
            continue
        data=glyph(char)
        if data is None:
            continue
        step=data[3]*font
        if width and lines[-1] and widths[-1]+step>width:
            carry=[]
            if char in CLOSING or lines[-1][-1][0] in OPENING:
                carry=[lines[-1].pop()]
                widths[-1]-=carry[0][1][3]*font
            lines.append(carry);widths.append(sum(v[1][3]*font for v in carry))
        lines[-1].append((char,data));widths[-1]+=step
    if max_lines:
        lines,widths=lines[:max_lines],widths[:max_lines]
    result=[]
    for row,line in enumerate(lines):
        x=0.
        for unused,data in line:
            result.append((data,row,x));x+=data[3]*font
    return result,widths
