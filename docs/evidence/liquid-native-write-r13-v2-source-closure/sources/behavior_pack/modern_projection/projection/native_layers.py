# -*- coding: utf-8 -*-
"""Adapt logical layers to native cells without introducing render proxies."""
from .block_registry import canonical, states
from .block_traits import is_snow_coverable, is_waterloggable
from .cell import AIR, _covered_snow, _water, actor_data, background, foreground, make_cell


def _snow_value(value, covered, cache):
    if cache is None:
        return _covered_snow(value, covered)
    key = (value, covered)
    if key not in cache:
        cache[key] = _covered_snow(value, covered)
    return cache[key]


def _native_pair(front, back, snow_cache=None, water_cache=None):
    if front == AIR:
        front, back = back, AIR
    elif back[0] == 'minecraft:snow_layer' and is_snow_coverable(front):
        front, back = back, front
    elif _water(front) and back != AIR:
        if water_cache is None:
            supported = is_waterloggable(back)
        else:
            if back not in water_cache:
                water_cache[back] = is_waterloggable(back)
            supported = water_cache[back]
        if supported:
            front, back = back, front
    if front[0] == 'minecraft:snow_layer':
        front = _snow_value(front, is_snow_coverable(back), snow_cache)
    return front, back


def native_cell(value):
    """Return a temporary native representation; logical data remains intact."""
    original_front, original_back = foreground(value), background(value)
    front, back = _native_pair(canonical(original_front), canonical(original_back))
    if front == original_front and back == original_back:
        return value
    return make_cell(front, back, actor_data(value))


def _replace_positions(entries, records, changes, other_records):
    if not changes:
        return
    for value, positions in list(entries.items()):
        remaining = [index for index in positions if index not in changes]
        if remaining:
            entries[value] = remaining
        else:
            entries.pop(value)
    for index, value in changes.items():
        if value != AIR:
            entries.setdefault(value, []).append(index)
    for value in set(changes.values()):
        if value == AIR:
            continue
        record = (states(value) if value[0] == 'minecraft:snow_layer' else
                  other_records[value] if value in other_records else states(value))
        if record is not None:
            records[value] = record


def _promote_standalone(common, common_states, extra, extra_states):
    occupied = set(index for value, positions in common.items()
                   if value != AIR for index in positions)
    for value, positions in list(extra.items()):
        if value == AIR:
            continue
        promoted = [index for index in positions if index not in occupied]
        if not promoted:
            continue
        remaining = [index for index in positions if index in occupied]
        common.setdefault(value, []).extend(promoted)
        if value in extra_states:
            common_states[value] = extra_states[value]
        if remaining:
            extra[value] = remaining
        else:
            extra.pop(value)
        if AIR in common:
            occupied.update(promoted)
    if AIR in common:
        common[AIR] = [index for index in common[AIR] if index not in occupied]
        if not common[AIR]:
            common.pop(AIR)


def normalize_palette_layers(common, common_states, extra, extra_states):
    """Normalize copied native palette maps before rendering or world writes."""
    snow_cache, water_cache = {}, {}
    if not extra:
        for value, positions in list(common.items()):
            if value[0] != 'minecraft:snow_layer':
                continue
            replacement, unused = _native_pair(value, AIR, snow_cache, water_cache)
            if replacement != value:
                common.pop(value)
                common.setdefault(replacement, []).extend(positions)
                common_states[replacement] = states(replacement)
        return
    has_snow = any(value[0] == 'minecraft:snow_layer' for value in list(common) + list(extra))
    if not has_snow and not any(_water(value) for value in common):
        _promote_standalone(common, common_states, extra, extra_states)
        return
    backs = dict((index, value) for value, positions in extra.items()
                 if value != AIR for index in positions)
    fronts = {}
    if backs:
        fronts = dict((index, value) for value, positions in common.items()
                      if value != AIR for index in positions if index in backs)
    front_changes, back_changes = {}, {}
    for index, back in backs.items():
        front = fronts.get(index, AIR)
        native_front, native_back = _native_pair(front, back, snow_cache, water_cache)
        if native_front != front:
            front_changes[index] = native_front
        if native_back != back:
            back_changes[index] = native_back
    for front, positions in common.items():
        if front[0] != 'minecraft:snow_layer':
            continue
        for index in positions:
            replacement, unused = _native_pair(front, backs.get(index, AIR), snow_cache, water_cache)
            if replacement != front:
                front_changes[index] = replacement
    old_common_states = dict(common_states)
    _replace_positions(common, common_states, front_changes, extra_states)
    _replace_positions(extra, extra_states, back_changes, old_common_states)
