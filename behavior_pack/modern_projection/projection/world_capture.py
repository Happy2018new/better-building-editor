# -*- coding: utf-8 -*-
"""Merge one native client palette chunk into a local building document."""
from __future__ import unicode_literals
from .cell import AIR, actor_data, background, foreground, make_cell
from .model import block
from .nbt_spatial import rebase
from .block_registry import from_states
from .visible_actor import compose_actor, entity_nbt, render_actor

UNKNOWN_NAMES = ('minecraft:unknown', b'minecraft:unknown')


def merge_entity_document(document, entities):
    if document is None or document.size != entities.size:
        raise ValueError('方块实体与客户端选区尺寸不匹配')
    changes = []
    for pos, captured in entities.blocks.items():
        current = document.get(pos)
        if foreground(current) != foreground(captured):
            raise ValueError('读取期间世界方块已变化，请重新导入选区')
        nbt = entity_nbt(actor_data(captured))
        actor = compose_actor(render_actor(actor_data(current)), nbt)
        changes.append((pos, make_cell(foreground(current), background(current), actor)))
    for pos, value in changes:
        document.blocks[pos] = value


def native_actor_cells(source, chunk_origin, chunk_size):
    sx, sy, sz = chunk_size
    if tuple(source.get('volume', ())) != (sz, sx, sy):
        raise ValueError('服务端方块实体 palette 尺寸无效')
    materials = {}
    records = _states(source, 'states')
    for value, positions in source.get('common', {}).items():
        material = _material(value, records)
        for index in positions:
            materials[index] = material
    for name, entries in source.get('actor', {}).items():
        if isinstance(name, bytes):
            name = name.decode('utf8')
        for index in entries:
            if type(index) is not int or not 0 <= index < sx * sy * sz:
                raise ValueError('服务端方块实体 palette 坐标无效')
            material = materials.get(index)
            if material is None or material[0] != name:
                raise ValueError('服务端方块实体 palette 名称不匹配')
            y, rem = divmod(index, sx * sz)
            x, z = divmod(rem, sz)
            yield add_local(chunk_origin, (x, y, z)), material


def add_local(origin, pos):
    return tuple(origin[i] + pos[i] for i in range(3))


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
