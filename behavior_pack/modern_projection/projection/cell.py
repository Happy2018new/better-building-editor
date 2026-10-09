# -*- coding: utf-8 -*-
"""Immutable complete cells with a backward-compatible foreground pair view.

NBT is stored as a tagged immutable tree, never a mutable SDK dictionary. The
tags preserve Python scalar/container types as well as explicit SDK NBT tags.
"""
from __future__ import unicode_literals
import base64
import math

AIR = ('minecraft:air', 0)
MAX_NBT_DEPTH = 64
MAX_NBT_NODES = 65536
try:
    integer_types = (int, long)
    text_type = unicode
except NameError:
    integer_types = (int,)
    text_type = str


def freeze(value, depth=0, budget=None):
    if budget is None:
        budget = [MAX_NBT_NODES]
    budget[0] -= 1
    if depth > MAX_NBT_DEPTH or budget[0] < 0:
        raise ValueError('方块实体数据过深或过大')
    if value is None:
        return ('null',)
    if type(value) is bool:
        return ('bool', value)
    if isinstance(value, integer_types):
        return ('int', str(value))
    if type(value) is float:
        if math.isnan(value) or math.isinf(value):
            raise ValueError('方块实体数据包含非有限数值')
        return ('float', value.hex())
    if isinstance(value, bytes):
        return ('bytes', base64.b64encode(value).decode('ascii'))
    if isinstance(value, text_type):
        return ('text', value)
    if type(value) in (list, tuple):
        return ('list' if type(value) is list else 'tuple',
                tuple(freeze(v, depth + 1, budget) for v in value))
    if type(value) is dict:
        pairs = [(freeze(k, depth + 1, budget), freeze(v, depth + 1, budget))
                 for k, v in value.items()]
        return ('dict', tuple(sorted(pairs)))
    raise ValueError('方块实体数据包含不支持的类型')


def thaw(value):
    tag = value[0]
    if tag == 'null':
        return None
    if tag == 'bool':
        return value[1]
    if tag == 'int':
        return int(value[1])
    if tag == 'float':
        return float.fromhex(value[1])
    if tag == 'bytes':
        return base64.b64decode(value[1].encode('ascii'))
    if tag == 'text':
        return value[1]
    if tag in ('list', 'tuple'):
        result = [thaw(v) for v in value[1]]
        return result if tag == 'list' else tuple(result)
    if tag == 'dict':
        return dict((thaw(k), thaw(v)) for k, v in value[1])
    raise ValueError('方块实体数据类型标签无效')


def _tree(value, depth=0, budget=None):
    """Validate a JSON-decoded tagged tree before allocating native objects."""
    if budget is None:
        budget = [MAX_NBT_NODES]
    budget[0] -= 1
    if depth > MAX_NBT_DEPTH or budget[0] < 0 or not isinstance(value, (list, tuple)) or not value:
        raise ValueError('方块实体编码无效或超限')
    tag = value[0]
    if tag == 'null' and len(value) == 1:
        return ('null',)
    if len(value) != 2:
        raise ValueError('方块实体类型标签无效')
    payload = value[1]
    if tag in ('list', 'tuple') and isinstance(payload, (list, tuple)):
        return (tag, tuple(_tree(v, depth + 1, budget) for v in payload))
    if tag == 'dict' and isinstance(payload, (list, tuple)):
        pairs = []
        for row in payload:
            if not isinstance(row, (list, tuple)) or len(row) != 2:
                raise ValueError('方块实体字典编码无效')
            pairs.append((_tree(row[0], depth + 1, budget), _tree(row[1], depth + 1, budget)))
        if len(set(k for k, v in pairs)) != len(pairs):
            raise ValueError('方块实体字典包含重复键')
        return ('dict', tuple(sorted(pairs)))
    if tag == 'bool' and type(payload) is bool:
        return (tag, payload)
    if tag in ('int', 'float', 'bytes', 'text') and isinstance(payload, text_type):
        result = (tag, payload)
        # A canonical round-trip rejects malformed base64 and numeric strings.
        if freeze(thaw(result)) == result:
            return result
    raise ValueError('方块实体标量编码无效')


class Cell(tuple):
    """Pair-compatible value; equality and hashing include every layer and NBT."""
    def __new__(cls, front, back=AIR, nbt=None):
        value = tuple.__new__(cls, front)
        object.__setattr__(value, '_background', tuple(back))
        object.__setattr__(value, '_actor', freeze(nbt))
        return value

    def __setattr__(self, name, value):
        raise AttributeError('Cell is immutable')

    @property
    def background(self):
        return self._background

    @property
    def nbt(self):
        return thaw(self._actor)

    def __eq__(self, other):
        return (isinstance(other, Cell) and tuple.__eq__(self, other)
                and self._background == other._background and self._actor == other._actor)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        return hash((tuple(self), self._background, self._actor))

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self):
        return 'Cell(%r, %r, %r)' % (tuple(self), self._background, self.nbt)


def foreground(value):
    return (value[0], value[1])


def background(value):
    return value.background if isinstance(value, Cell) else AIR


def actor_data(value):
    return value.nbt if isinstance(value, Cell) else None


def make_cell(front=AIR, back=AIR, nbt=None):
    from .model import block
    front, back = block(foreground(front)), block(foreground(back))
    if front == AIR and nbt is not None:
        raise ValueError('空气前景不能携带方块实体数据')
    return front if back == AIR and nbt is None else Cell(front, back, nbt)


def layer(value, index=0):
    if index not in (0, 1):
        raise ValueError('方块层索引必须为 0 或 1')
    return foreground(value) if index == 0 else background(value)


def replace_layer(value, material, index=0):
    front, back = foreground(value), background(value)
    nbt = actor_data(value)
    if index == 0:
        replacement = foreground(material)
        if replacement[0] != front[0] or replacement == AIR:
            nbt = None
        front = replacement
    elif index == 1:
        back = foreground(material)
    else:
        raise ValueError('方块层索引必须为 0 或 1')
    return make_cell(front, back, nbt)


def encode(value):
    if not isinstance(value, Cell):
        return list(value)
    return {'foreground': list(value), 'background': list(value.background), 'nbt': value._actor}


def decode(value):
    from .model import block
    if not isinstance(value, dict):
        return block(value)
    if set(value) != set(('foreground', 'background', 'nbt')):
        raise ValueError('完整方块数据字段无效')
    return make_cell(block(value['foreground']), block(value['background']), thaw(_tree(value['nbt'])))


def has_complete_cells(store):
    return any(isinstance(value, Cell) for value in store.palette)


def transform(value, tool):
    from .state_transform import transform as transform_block
    return make_cell(transform_block(foreground(value), tool),
                     transform_block(background(value), tool), actor_data(value))
