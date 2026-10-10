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
    from .block_groups import hydrate_chest_actor
    if document is None or document.size != entities.size:
        raise ValueError('方块实体与客户端选区尺寸不匹配')
    changes = []
    for pos, captured in entities.blocks.items():
        current = document.get(pos)
        if foreground(current) != foreground(captured):
            raise ValueError('读取期间世界方块已变化，请重新导入选区')
        nbt = entity_nbt(actor_data(captured))
        actor = compose_actor(render_actor(actor_data(current)), nbt)
        changes.append((pos, hydrate_chest_actor(
            make_cell(foreground(current), background(current), actor), pos)))
    for pos, value in changes:
        document.blocks[pos] = value


def native_actor_cells(source, chunk_origin, chunk_size):
    sx, sy, sz = chunk_size
    fronts, backs = native_palette_layers(source, chunk_size)
    for index, name, payload in native_palette_actors(source, fronts, backs, sx * sy * sz):
        y, rem = divmod(index, sx * sz)
        x, z = divmod(rem, sz)
        yield add_local(chunk_origin, (x, y, z)), fronts[index]


def add_local(origin, pos):
    return tuple(origin[i] + pos[i] for i in range(3))


def restore_omitted_palette_cells(document, source, chunk_origin, chunk_size,
                                  world_origin, read_block):
    """Read actual cells omitted by the native door/bed palette exporter."""
    sx, sy, sz = chunk_size
    recorded = set(index for positions in source.get('common', {}).values()
                   for index in positions)
    for index in range(sx * sy * sz):
        if index in recorded:
            continue
        y, rem = divmod(index, sx * sz)
        x, z = divmod(rem, sz)
        pos = add_local(chunk_origin, (x, y, z))
        actual = read_block(add_local(world_origin, pos))
        if not actual or actual[0] in UNKNOWN_NAMES:
            raise ValueError('无法读取 palette 省略的方块，请靠近后重新导入')
        material = block(actual)
        if material != AIR:
            current = document.get(pos)
            document.blocks[pos] = make_cell(material, background(current), actor_data(current))


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


def native_palette_layers(source, chunk_size):
    sx, sy, sz = chunk_size
    if tuple(source.get('volume', ())) != (sz, sx, sy):
        raise ValueError('世界方块 palette 尺寸无效')
    volume = sx * sy * sz
    layers = []
    for layer, state_key in (('common', 'states'), ('extra', 'extraStates')):
        materials = {}
        records = _states(source, state_key)
        for value, positions in source.get(layer, {}).items():
            material = _material(value, records)
            for index in positions:
                if type(index) is not int or not 0 <= index < volume:
                    raise ValueError('世界方块 palette 包含无效坐标')
                if index in materials:
                    raise ValueError('世界方块 palette 包含重复坐标')
                materials[index] = material
        layers.append(materials)
    return tuple(layers)


def native_palette_actors(source, fronts, backs, volume):
    from .native_palette_actor import resolve_name
    result, seen = [], set()
    for name, entries in source.get('actor', {}).items():
        name = _state_text(name)
        for index, payload in entries.items():
            if type(index) is not int or not 0 <= index < volume:
                raise ValueError('方块实体 palette 坐标无效')
            if index in seen:
                raise ValueError('方块实体 palette 包含重复坐标')
            seen.add(index)
            resolved = resolve_name(name, fronts.get(index, AIR), backs.get(index, AIR))
            result.append((index, resolved, payload))
    return result


def merge_palette(document, source, chunk_origin, chunk_size, world_origin):
    """Copy native foreground, background and actor data into ``document``."""
    sx, sy, sz = chunk_size
    volume = sx * sy * sz
    fronts, backs = native_palette_layers(source, chunk_size)
    actors = native_palette_actors(source, fronts, backs, volume)

    def local_pos(index):
        if type(index) is not int or not 0 <= index < volume:
            raise ValueError('世界方块 palette 包含无效坐标')
        y, rem = divmod(index, sx * sz)
        x, z = divmod(rem, sz)
        return (chunk_origin[0] + x, chunk_origin[1] + y, chunk_origin[2] + z)

    for index, material in fronts.items():
        if material == AIR:
            continue
        pos = local_pos(index)
        current = document.get(pos)
        if foreground(current) != AIR:
            raise ValueError('世界方块 palette 在前景层包含重复坐标')
        document.blocks[pos] = make_cell(material, background(current), actor_data(current))

    for index, material in backs.items():
        if material == AIR:
            continue
        pos = local_pos(index)
        current = document.get(pos)
        if background(current) != AIR:
            raise ValueError('世界方块 palette 在背景层包含重复坐标')
        document.blocks[pos] = make_cell(foreground(current), material, actor_data(current))

    for index, name, payload in actors:
        pos = local_pos(index)
        current = document.get(pos)
        actor = rebase(payload, tuple(-value for value in world_origin))
        document.blocks[pos] = make_cell(foreground(current), background(current), actor)
