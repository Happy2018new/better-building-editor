# -*- coding: utf-8 -*-
"""Authoritative native name/aux/states; archived aliases are input-only."""
from __future__ import unicode_literals
import base64
import json
import zlib
from .block_registry_data import BLOCKS, DEFAULT_AUX, ALIASES, SOURCE_SHA256, RECORD_COUNT

_records, _aliases = {}, {}


def _decode(name, source, cache):
    if name not in cache:
        packed = source.get(name)
        rows = json.loads(zlib.decompress(base64.b64decode(packed))) if packed else []
        cache[name] = dict((int(key), value) for key, value in rows)
    return cache[name]


def aux_values(name):
    return tuple(sorted(_decode(name, BLOCKS, _records)))


def canonical(value):
    name, aux = value
    records = _decode(name, BLOCKS, _records)
    if aux in records:
        return value
    alias = _decode(name, ALIASES, _aliases).get(aux)
    if alias is not None:
        return tuple(alias)
    if name.startswith('minecraft:'):
        raise ValueError('方块或附加值不在当前方块表中：%s [%d]' % value)
    # Mod blocks have their own definitions and keep the SDK extension path.
    return value


def states(value):
    name, aux = canonical(value)
    record = _decode(name, BLOCKS, _records).get(aux)
    if record is None:
        return None
    # Native SerializeBlockPalette uses bool for NBT byte, int for NBT int.
    return dict((key, bool(val) if kind == 'byte' else val) for key,kind,val in record)


def catalogue_values():
    # Colors/species are separate modern names. State variants are edited with
    # the aux control, instead of thousands of duplicate inventory tiles.
    return sorted(DEFAULT_AUX.items())


def next_aux(value, delta):
    value = canonical(value)
    valid = aux_values(value[0])
    if not valid:
        return (value[0], max(0,min(32767,value[1]+delta)))
    index = valid.index(value[1])
    return (value[0], valid[max(0,min(len(valid)-1,index+delta))])
