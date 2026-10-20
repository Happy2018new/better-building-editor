# -*- coding: utf-8 -*-
"""Authoritative native name/aux/states; archived aliases are input-only."""
from __future__ import unicode_literals
import base64
import json
import zlib
from .block_registry_data import BLOCKS, DEFAULT_AUX, ALIASES, SOURCE_SHA256, SOURCE_VERSION, RECORD_COUNT

_records, _aliases, _reverse = {}, {}, {}


def _decode(name, source, cache):
    if name not in cache:
        packed = source.get(name)
        rows = json.loads(zlib.decompress(base64.b64decode(packed))) if packed else []
        cache[name] = dict((int(key), value) for key, value in rows)
    return cache[name]


def aux_values(name):
    return tuple(sorted(_decode(name, BLOCKS, _records)))


def try_canonical(value):
    """Resolve a stored pair without rejecting unknown historical vanilla data."""
    name, aux = value
    records = _decode(name, BLOCKS, _records)
    if aux in records:
        return value
    alias = _decode(name, ALIASES, _aliases).get(aux)
    if alias is not None:
        return tuple(alias)
    if name.startswith('minecraft:'):
        return None
    # Mod blocks have their own definitions and keep the SDK extension path.
    return value


def canonical(value):
    result = try_canonical(value)
    if result is None:
        raise ValueError('方块或附加值不在当前方块表中：%s [%d]' % value)
    return result


def states(value):
    name, aux = canonical(value)
    record = _decode(name, BLOCKS, _records).get(aux)
    if record is None:
        return None
    # Native SerializeBlockPalette uses bool for NBT byte, int for NBT int.
    return dict((key, bool(val) if kind == 'byte' else val) for key,kind,val in record)


def _state_key(properties):
    # bool and int must remain distinct: the SDK serializes NBT byte/int
    # differently even when Python compares their values equal.
    return tuple(sorted((key, type(value).__name__, value)
                        for key, value in properties.items()))


def from_states(name, properties):
    """Resolve semantic states against this version's table, never aux arithmetic."""
    if name not in _reverse:
        values = {}
        for aux in aux_values(name):
            values.setdefault(_state_key(states((name, aux))), aux)
        _reverse[name] = values
    aux = _reverse[name].get(_state_key(properties))
    return (name, aux) if aux is not None else None


def fingerprint():
    return SOURCE_SHA256


def source_version():
    return SOURCE_VERSION


def catalogue_values():
    # Colors/species are separate modern names. State variants are edited with
    # the aux control, instead of thousands of duplicate inventory tiles.
    # Render-only proxies share this registry but are not user-placeable.
    return sorted((name, aux) for name, aux in DEFAULT_AUX.items()
                  if not name.startswith('modern_projection:preview_'))


def next_aux(value, delta):
    value = canonical(value)
    valid = aux_values(value[0])
    if not valid:
        return (value[0], max(0,min(32767,value[1]+delta)))
    index = valid.index(value[1])
    return (value[0], valid[max(0,min(len(valid)-1,index+delta))])
