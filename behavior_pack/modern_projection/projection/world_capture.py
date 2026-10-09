# -*- coding: utf-8 -*-
"""Merge one native client palette chunk into a local building document."""
from __future__ import unicode_literals
from .cell import AIR, actor_data, background, foreground, make_cell
from .model import block
from .nbt_spatial import rebase
from .block_registry import from_states

UNKNOWN_NAMES = ('minecraft:unknown', b'minecraft:unknown')


def validate_loaded_chunk(loaded_chunks, dimension, low, high, read_block):
    """Reject chunks whose air data could be caused by client unloads."""
    if loaded_chunks is None:
        raise ValueError('无法确认世界区块已加载，请靠近选区后重试')
    xs, ys, zs = set((low[0], high[0])), set((low[1], high[1])), set((low[2], high[2]))
    for x in xs:
        for z in zs:
            if (dimension, x >> 4, z >> 4) not in loaded_chunks:
                raise ValueError('世界选区包含未加载区块，请靠近选区后重试')
    for x in xs:
        for y in ys:
            for z in zs:
                value = read_block((x, y, z))
                if not value or value[0] in UNKNOWN_NAMES:
                    raise ValueError('世界选区状态尚未加载，请靠近选区后重试')


def _states(source, name):
    values = {}
    for value, record in source.get(name, {}).items():
        values[block(value)] = _normalize_state_record(record)
    return values


def _state_text(value):
    if isinstance(value, bytes):
        return value.decode('utf8')
    return value


def _normalize_state_record(record):
    if not isinstance(record, dict):
        return record
    return dict((_state_text(key), _state_text(value))
                for key, value in record.items())


def _material(value, states):
    pair = block(value)
    record = states.get(pair)
    if record is None:
        return pair
    resolved = from_states(pair[0], record)
    if resolved is None:
        raise ValueError('方块状态不在当前版本表中，无法完整导入：%s' % pair[0])
    return resolved


def merge_palette(document, source, chunk_origin, chunk_size, world_origin):
    """Copy native foreground, background and actor data into ``document``."""
    sx, sy, sz = chunk_size
    if tuple(source.get('volume', ())) != (sz, sx, sy):
        raise ValueError('世界方块 palette 尺寸无效')
    volume = sx * sy * sz
    front_states = _states(source, 'states')
    back_states = _states(source, 'extraStates')

    def local_pos(index):
        if type(index) is not int or not 0 <= index < volume:
            raise ValueError('世界方块 palette 包含无效坐标')
        y, rem = divmod(index, sx * sz)
        x, z = divmod(rem, sz)
        return (chunk_origin[0] + x, chunk_origin[1] + y, chunk_origin[2] + z)

    for value, positions in source.get('common', {}).items():
        material = _material(value, front_states)
        if material == AIR:
            continue
        for index in positions:
            pos = local_pos(index)
            current = document.get(pos)
            if foreground(current) != AIR:
                raise ValueError('世界方块 palette 在前景层包含重复坐标')
            document.blocks[pos] = make_cell(material, background(current), actor_data(current))

    for value, positions in source.get('extra', {}).items():
        material = _material(value, back_states)
        if material == AIR:
            continue
        for index in positions:
            pos = local_pos(index)
            current = document.get(pos)
            if background(current) != AIR:
                raise ValueError('世界方块 palette 在背景层包含重复坐标')
            document.blocks[pos] = make_cell(foreground(current), material, actor_data(current))

    for name, entries in source.get('actor', {}).items():
        if isinstance(name, bytes):
            name = name.decode('utf8')
        for index, payload in entries.items():
            pos = local_pos(index)
            current = document.get(pos)
            if foreground(current) == AIR or foreground(current)[0] != name:
                raise ValueError('方块实体与其前景方块不匹配：%s' % name)
            actor = rebase(payload, tuple(-value for value in world_origin))
            document.blocks[pos] = make_cell(foreground(current), background(current), actor)
