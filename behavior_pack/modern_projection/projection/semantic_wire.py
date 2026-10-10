# -*- coding: utf-8 -*-
"""Versioned semantic materials shared by configs, packets and clipboard data."""
from __future__ import unicode_literals
import re
from . import block_registry as registry
from .cell import AIR, Cell, foreground, background, make_cell, thaw, _tree

CELL_VERSION = 1
MAX_MATERIALS = 131072
IDENTIFIER = re.compile(r'^[a-z0-9_.-]+:[a-z0-9_./-]+$')


def provenance():
    return {'version': registry.source_version(), 'sha256': registry.fingerprint()}


def validate_header(data):
    source = data.get('registry')
    if (data.get('cellVersion') != CELL_VERSION or type(data.get('cellVersion')) is not int or
            not isinstance(source, dict) or set(source) != set(('version', 'sha256')) or
            not isinstance(source['version'], type('')) or not 1 <= len(source['version']) <= 128 or
            not isinstance(source['sha256'], type('')) or
            not re.match(r'^[0-9a-fA-F]{64}$', source['sha256'])):
        raise ValueError('语义方块格式或来源方块表版本无效')
    return source


def _material_pair(value):
    if (not isinstance(value, (list, tuple)) or len(value) != 2 or
            not isinstance(value[0], type('')) or len(value[0]) > 160 or
            not IDENTIFIER.match(value[0]) or type(value[1]) is not int or not 0 <= value[1] <= 32767):
        raise ValueError('语义材质包含无效的方块标识或附加值')
    return tuple(value)


def encode_material(value):
    value = _material_pair(value)
    canonical = registry.canonical(value)
    properties = registry.states(canonical)
    if properties is None:
        return list(value)
    result = [canonical[0], properties]
    if canonical != value:
        result.append(list(value))
    return result


def decode_material(row, source):
    if not isinstance(row, (list, tuple)) or len(row) not in (2, 3):
        raise ValueError('语义材质记录无效')
    name, properties = row[:2]
    if type(properties) is int:
        value = _material_pair(row)
        if name.startswith('minecraft:'):
            raise ValueError('原版语义材质缺少方块状态')
        return value
    if (not isinstance(name, type('')) or len(name) > 160 or not IDENTIFIER.match(name) or
            not isinstance(properties, dict) or len(properties) > 128):
        raise ValueError('语义方块状态无效')
    for key, value in properties.items():
        if (not isinstance(key, type('')) or not 1 <= len(key) <= 160 or
                type(value) not in (bool, int, type('')) or
                (isinstance(value, type('')) and len(value) > 160)):
            raise ValueError('语义方块状态键或值无效')
    resolved = registry.from_states(name, properties)
    if resolved is None:
        raise ValueError('当前方块表无法表示 %s 的状态 %r（来源 %s）' %
                         (name, properties, source['version']))
    if len(row) == 3:
        hint = _material_pair(row[2])
        # Preserve an archived alias only while it denotes the exact semantic
        # state in this registry. Aux is never trusted after a version change.
        try:
            equivalent = registry.canonical(hint) == resolved
        except ValueError:
            equivalent = False
        if equivalent:
            return hint
    return resolved


class Encoder(object):
    def __init__(self):
        self.materials = []
        self.ids = {}

    def material_id(self, value):
        identity = self.ids.get(value)
        if identity is None:
            if len(self.materials) >= MAX_MATERIALS:
                raise ValueError('语义材质数量超过限制')
            identity = len(self.materials)
            self.ids[value] = identity
            self.materials.append(encode_material(value))
        return identity

    def cell(self, value):
        front = self.material_id(foreground(value))
        if not isinstance(value, Cell):
            return front
        back = self.material_id(background(value))
        return [front, back] if value._actor == ('null',) else [front, back, value._actor]


def decode_cell(row, materials):
    if type(row) is int:
        identities, actor = [row], None
    elif isinstance(row, (list, tuple)) and len(row) in (2, 3):
        identities = row[:2]
        actor = thaw(_tree(row[2])) if len(row) == 3 else None
    else:
        raise ValueError('语义完整方块记录无效')
    if any(type(identity) is not int or not 0 <= identity < len(materials) for identity in identities):
        raise ValueError('语义方块包含未知材质')
    front = materials[identities[0]]
    back = materials[identities[1]] if len(identities) == 2 else AIR
    return make_cell(front, back, actor)


def append_palette(store, value, mapping):
    """Merge semantic aliases while retaining source IDs for chunk remapping."""
    if not mapping and value != AIR:
        raise ValueError('语义材质表缺少空气')
    identity = store.palette_ids.get(value)
    if identity is None:
        identity = len(store.palette)
        store.palette_ids[value] = identity
        store.palette.append(value)
    mapping.append(identity)
