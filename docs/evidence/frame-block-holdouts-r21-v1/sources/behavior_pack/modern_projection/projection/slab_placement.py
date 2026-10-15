# -*- coding: utf-8 -*-
"""Semantic slab placement; registry states own aux values and legacy aliases."""
from __future__ import unicode_literals
from . import block_registry as registry

SCHEMA_VERSION = 1
HALF_STATE = 'minecraft:vertical_half'
_halves = {}
_doubles = {}


def slab_half(material):
    """Return a single slab's half; doubles retain a redundant half in Bedrock."""
    name, aux = material
    if not name.startswith('minecraft:') or 'slab' not in name:
        return None
    key = (name, aux)
    if key not in _halves:
        canonical = registry.try_canonical(key)
        properties = registry.states(canonical) if canonical is not None else None
        _halves[key] = (properties.get(HALF_STATE) if properties is not None and
                        'double' not in canonical[0].split(':', 1)[1].split('_') else None)
    return _halves[key]


def placed_slab(material, normal, point=None):
    """A bottom-face click places a top slab; side clicks use their local Y."""
    if slab_half(material) is None or normal == (0, 0, 0):
        return material
    half = 'top' if normal[1] < 0 else 'bottom'
    if not normal[1] and point is not None:
        half = 'top' if point[1] > .5 else 'bottom'
    canonical = registry.canonical(material)
    properties = registry.states(canonical)
    properties[HALF_STATE] = half
    result = registry.from_states(canonical[0], properties)
    if result is None:
        raise ValueError('当前方块表缺少对应上／下半砖状态')
    return result


def merged_slab(existing, requested):
    """Merge the same material only; resolve names and states against the dump."""
    if slab_half(existing) is None or slab_half(requested) is None:
        return None
    existing, requested = registry.canonical(existing), registry.canonical(requested)
    if existing[0] != requested[0]:
        return None
    name = existing[0]
    if name not in _doubles:
        # Native families use *_double_slab, while copper uses *double_cut_*.
        # A candidate must exist in this version's dump; this is not a whitelist.
        candidates = (name[:-5] + '_double_slab',
                      name.replace('cut_copper_slab', 'double_cut_copper_slab'))
        matches = tuple(candidate for candidate in candidates if candidate != name and
                        candidate in registry.BLOCKS)
        _doubles[name] = matches[0] if len(set(matches)) == 1 else None
    double = _doubles[name]
    if double is None:
        raise ValueError('当前方块表缺少唯一对应的双半砖，需要更新半砖规则')
    properties = registry.states(existing)
    properties[HALF_STATE] = 'bottom'
    result = registry.from_states(double, properties)
    if result is None:
        raise ValueError('当前方块表缺少对应双半砖状态')
    return result


def fills_clicked_half(existing, normal):
    half = slab_half(existing)
    return ((half == 'bottom' and normal[1] > 0) or
            (half == 'top' and normal[1] < 0))
