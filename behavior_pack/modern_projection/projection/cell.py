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
MAX_NBT_BYTES = 4 * 1024 * 1024
try:
    integer_types = (int, long)
    text_type = unicode
except NameError:
    integer_types = (int,)
    text_type = str


def _consume(budget, amount):
    budget[1] -= amount
    if budget[1] < 0:
        raise ValueError('方块实体数据过大')


def freeze(value, depth=0, budget=None):
    if budget is None:
        budget = [MAX_NBT_NODES, MAX_NBT_BYTES]
    budget[0] -= 1
    if depth > MAX_NBT_DEPTH or budget[0] < 0 or budget[1] < 0:
        raise ValueError('方块实体数据过深或过大')
    if value is None:
        return ('null',)
    if type(value) is bool:
        return ('bool', value)
    if isinstance(value, integer_types):
        result = str(value)
        _consume(budget, len(result))
        return ('int', result)
    if type(value) is float:
        if math.isnan(value) or math.isinf(value):
            raise ValueError('方块实体数据包含非有限数值')
        result = value.hex()
        _consume(budget, len(result))
        return ('float', result)
    if isinstance(value, bytes):
        _consume(budget, len(value))
        return ('bytes', base64.b64encode(value).decode('ascii'))
    if isinstance(value, text_type):
        _consume(budget, len(value.encode('utf8')))
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


def _tree_memory_bytes(value):
    tag = value[0]
    if tag in ('null', 'bool'):
        return 32
    if tag in ('int', 'float', 'text', 'bytes'):
        return 48 + len(value[1].encode('utf8'))
    if tag in ('list', 'tuple'):
        return 64 + sum(_tree_memory_bytes(child) for child in value[1])
    if tag == 'dict':
        return 80 + sum(_tree_memory_bytes(key) + _tree_memory_bytes(child)
                        for key, child in value[1])
    raise ValueError('方块实体数据类型标签无效')


def _tree(value, depth=0, budget=None):
    """Validate a JSON-decoded tagged tree before allocating native objects."""
    if budget is None:
        budget = [MAX_NBT_NODES, MAX_NBT_BYTES]
    budget[0] -= 1
    if (depth > MAX_NBT_DEPTH or budget[0] < 0 or budget[1] < 0 or
            not isinstance(value, (list, tuple)) or not value):
        raise ValueError('方块实体编码无效或超限')
    tag = value[0]
    if not isinstance(tag, text_type):
        raise ValueError('方块实体类型标签无效')
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
        keys = []
        try:
            for key, unused in pairs:
                native = thaw(key)
                hash(native)
                keys.append(native)
        except (TypeError, ValueError):
            raise ValueError('方块实体字典键无效')
        if len(set(keys)) != len(keys):
            raise ValueError('方块实体字典包含重复键')
        return ('dict', tuple(sorted(pairs)))
    if tag == 'bool' and type(payload) is bool:
        return (tag, payload)
    if tag in ('int', 'float', 'bytes', 'text') and isinstance(payload, text_type):
        if tag == 'bytes':
            try:
                _consume(budget, len(base64.b64decode(payload.encode('ascii'))))
            except (ValueError, UnicodeError):
                raise ValueError('方块实体字节数据编码无效')
        elif tag == 'text':
            _consume(budget, len(payload.encode('utf8')))
        else:
            _consume(budget, len(payload))
        result = (tag, payload)
        # A canonical round-trip rejects malformed base64 and numeric strings.
        if freeze(thaw(result)) == result:
            return result
    raise ValueError('方块实体标量编码无效')


class Cell(tuple):
    """Pair-compatible value; equality and hashing include every layer and NBT."""
    def __new__(cls, front, back=AIR, nbt=None):
        value = tuple.__new__(cls, front)
        actor = freeze(nbt)
        object.__setattr__(value, '_background', tuple(back))
        object.__setattr__(value, '_actor', actor)
        object.__setattr__(value, '_actor_bytes', _tree_memory_bytes(actor))
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

    def memory_bytes(self):
        names = (self[0][0], self._background[0])
        return (160 + sum(len(name.encode('utf8')) + 40 for name in names) +
                self._actor_bytes)

    def __copy__(self):
        return self

    def __deepcopy__(self, memo):
        return self

    def __repr__(self):
        return 'Cell(%r, %r, %r)' % (tuple(self), self._background, self.nbt)


def foreground(value):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError('无效的方块数据')
    return (value[0], value[1])


def background(value):
    return value.background if isinstance(value, Cell) else AIR


def actor_data(value):
    return value.nbt if isinstance(value, Cell) else None


def rebase(value, delta):
    if not isinstance(value, Cell) or actor_data(value) is None:
        return value
    from .nbt_spatial import rebase as rebase_actor
    return make_cell(foreground(value), background(value), rebase_actor(actor_data(value), delta))


def make_cell(front=AIR, back=AIR, nbt=None):
    from .model import block
    front, back = block(foreground(front)), block(foreground(back))
    if front == AIR and nbt is not None:
        raise ValueError('空气前景不能携带方块实体数据')
    return front if back == AIR and nbt is None else Cell(front, back, nbt)


def layer(value, index=0):
    if type(index) is not int or index not in (0, 1, 2):
        raise ValueError('方块层索引必须为 0、1 或 2')
    if index == 2:
        return foreground(value) if foreground(value) != AIR else background(value)
    return foreground(value) if index == 0 else background(value)


def replace_layer(value, material, index=0):
    if type(index) is not int or index not in (0, 1):
        raise ValueError('方块层索引必须为 0 或 1')
    front, back = foreground(value), background(value)
    nbt = actor_data(value)
    if index == 0:
        replacement = foreground(material)
        if replacement[0] != front[0] or replacement == AIR:
            nbt = None
        front = replacement
    else:
        back = foreground(material)
    return make_cell(front, back, nbt)


def _snow(material):
    return material[0] == 'minecraft:snow_layer'


def _covered_snow(material, covered):
    from .block_registry import from_states, states
    properties = states(material)
    if properties is None or 'covered_bit' not in properties:
        return material
    properties['covered_bit'] = covered
    result = from_states(material[0], properties)
    if result is None:
        raise ValueError('当前方块表缺少对应含雪状态')
    return result


def edit_cell(value, material, index=0):
    """Edit a selected layer, or compose native cells in automatic mode."""
    if type(index) is not int or index not in (0, 1, 2):
        raise ValueError('方块层索引必须为 0、1 或 2')
    if index == 2:
        return _edit_auto(value, material)
    result = replace_layer(value, material, index)
    if _snow(foreground(result)):
        from .block_traits import is_snow_coverable
        front = _covered_snow(foreground(result), is_snow_coverable(background(result)))
        result = make_cell(front, background(result), actor_data(result))
    return result


def _water(material):
    return material[0] in ('minecraft:water', 'minecraft:flowing_water')


def can_compose(value, material):
    """Whether automatic placement belongs inside the clicked existing cell."""
    from .block_traits import is_snow_coverable, is_waterloggable
    front, replacement = layer(value, 2), foreground(material)
    return ((_water(replacement) and is_waterloggable(front)) or
            (_water(front) and is_waterloggable(replacement)) or
            (_snow(front) and is_snow_coverable(replacement)) or
            (_snow(replacement) and (is_snow_coverable(front) or
             (_snow(front) and is_snow_coverable(background(value))))))


def _edit_auto(value, material):
    from .block_traits import is_snow_coverable, is_waterloggable
    front, back, replacement = foreground(value), background(value), foreground(material)
    if front == AIR:
        front, back = back, AIR
        value = make_cell(front)
    covered_plant = _snow(front) and is_snow_coverable(back)
    if replacement == AIR:
        if covered_plant or _water(back):
            return make_cell(back)
        return replace_layer(value, AIR)
    if _snow(front) and is_snow_coverable(replacement):
        return make_cell(_covered_snow(front, True), replacement)
    if _snow(replacement):
        plant = back if covered_plant else front
        if is_snow_coverable(plant):
            return make_cell(_covered_snow(replacement, True), plant)
        replacement = _covered_snow(replacement, False)
    if _water(replacement) and is_waterloggable(front):
        return replace_layer(value, replacement, 1)
    if _water(front) and is_waterloggable(replacement):
        return make_cell(replacement, front)
    result = replace_layer(value, replacement)
    if covered_plant or (_water(back) and not is_waterloggable(replacement)):
        result = make_cell(foreground(result), AIR, actor_data(result))
    return result


def encode(value):
    if not isinstance(value, Cell):
        return list(value)
    return [list(value), list(value.background), value._actor]


def decode(value):
    from .model import block
    if not isinstance(value, dict):
        if isinstance(value, (list, tuple)) and len(value) == 3:
            return make_cell(block(value[0]), block(value[1]), thaw(_tree(value[2])))
        return block(value)
    if set(value) != set(('foreground', 'background', 'nbt')):
        raise ValueError('完整方块数据字段无效')
    return make_cell(block(value['foreground']), block(value['background']), thaw(_tree(value['nbt'])))


def has_complete_cells(store):
    return any(isinstance(value, Cell) and store.counts.get(value, 0) > 0
               for value in store.palette)


def transform(value, tool, origin=None):
    from .state_transform import transform as transform_block
    nbt = actor_data(value)
    if nbt is not None and origin is not None:
        from .nbt_spatial import transform_pair
        nbt = transform_pair(nbt, origin, tool)
    return make_cell(transform_block(foreground(value), tool),
                     transform_block(background(value), tool), nbt)
