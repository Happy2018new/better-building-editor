# -*- coding: utf-8 -*-
"""Detached whole-building snapshots for projection and real-world placement.

The document's minimum corner remains the local origin. Quarter turns exchange
X/Z extents; native state and actor semantics stay owned by ``cell.transform``.
Snapshots preserve incomplete input parts without inventing their partners.
"""
from __future__ import unicode_literals

from .cell import actor_data, rebase as rebase_cell, transform as transform_cell
from .model import Document, MAX_AXES
from .state_transform import OPERATIONS


def validate_operations(operations=()):
    """Freeze an ordered sequence of existing transform IDs or reject it."""
    if not isinstance(operations, (tuple, list)):
        raise ValueError('投影变换必须是有序操作列表')
    result = tuple(operations)
    if any(operation not in OPERATIONS for operation in result):
        raise ValueError('投影包含不支持的旋转或镜像操作')
    return result


def _size(size):
    if (not isinstance(size, (tuple, list)) or len(size) != 3 or
            any(type(value) is not int or not 1 <= value <= MAX_AXES[axis]
                for axis, value in enumerate(size))):
        raise ValueError('投影建筑范围无效')
    return tuple(size)


def _next_size(size, operation):
    return (size[2], size[1], size[0]) if operation in (
        'rotate_y90', 'rotate_y270') else size


def transform_size(size, operations=()):
    result = _size(size)
    for operation in validate_operations(operations):
        result = _next_size(result, operation)
    return result


def _target(position, size, operation):
    x, y, z = position
    if operation == 'rotate_y90':
        return size[2] - 1 - z, y, x
    if operation == 'rotate_y180':
        return size[0] - 1 - x, y, size[2] - 1 - z
    if operation == 'rotate_y270':
        return z, y, size[0] - 1 - x
    axis = 'xyz'.index(operation[-1])
    result = list(position)
    result[axis] = size[axis] - 1 - result[axis]
    return tuple(result)


def transform_position(position, size, operations=()):
    dimensions = _size(size)
    if (not isinstance(position, (tuple, list)) or len(position) != 3 or
            any(type(value) is not int or not 0 <= value < dimensions[axis]
                for axis, value in enumerate(position))):
        raise ValueError('投影坐标超出建筑范围')
    result = tuple(position)
    for operation in validate_operations(operations):
        result = _target(result, dimensions, operation)
        dimensions = _next_size(dimensions, operation)
    return result


def _capture(document):
    if not isinstance(document, Document):
        raise ValueError('投影需要完整建筑文档')
    result = Document(document.size, name=document.name, biome=document.biome)
    result.blocks = document.blocks.copy()
    return result


def iter_snapshot(document, operations=()):
    """Capture now; yield work steps, then one final detached ``Document``.

    This outer function deliberately is not a generator: later draft edits
    cannot change the source while the caller waits for its first frame slot.
    Abandoning the returned iterator publishes no partial document.
    """
    selected = validate_operations(operations)
    source = _capture(document)
    return _snapshot_steps(source, selected)


def _snapshot_steps(source, operations):
    if not operations:
        yield source
        return
    dimensions = []
    size = source.size
    for operation in operations:
        dimensions.append(size)
        size = _next_size(size, operation)
    result = Document(size, name=source.name, biome=source.biome)
    plain_values = {}
    for position, value in source.blocks.items():
        if not source.contains(position):
            raise ValueError('方块超出建筑范围，已停止生成投影')
        plain = plain_values.get(value)
        if plain is None and actor_data(value) is None:
            # Immutable complete cells without an actor have no origin-dependent
            # data. One entry per used source palette value covers both layers.
            plain = value
            for operation in operations:
                plain = transform_cell(plain, operation)
            plain_values[value] = plain
        current = position
        for operation, size in zip(operations, dimensions):
            target = _target(current, size, operation)
            if plain is None:
                value = transform_cell(value, operation, current)
                value = rebase_cell(value, tuple(target[axis] - current[axis]
                                                for axis in range(3)))
            current = target
        result.blocks[current] = plain if plain is not None else value
        yield None
    yield result


def snapshot(document, operations=()):
    """Build a detached result synchronously for non-frame-driven callers."""
    result = None
    for step in iter_snapshot(document, operations):
        if step is not None:
            result = step
    return result
