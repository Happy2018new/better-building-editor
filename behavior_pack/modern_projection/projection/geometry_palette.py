# -*- coding: utf-8 -*-
"""Native render palettes; document and world block identities stay intact."""
from .block_registry import canonical, states
from .block_traits import is_snow_coverable
from .cell import AIR, _covered_snow
from .visible_actor import render_actor


# Snow-covered native leaves can lose faces in CombineBlockPaletteToGeometry.
# Ordinary hidden blocks preserve the species texture without that tessellator.
# Persistent/update flags affect leaf lifetime only, so all four native states
# share one render block. Canonicalization resolves both legacy leaf families.
LEAF_PROXIES = dict(('minecraft:' + name, 'modern_projection:preview_' + name)
                    for name in ('oak_leaves', 'spruce_leaves', 'birch_leaves',
                                 'jungle_leaves', 'acacia_leaves', 'dark_oak_leaves',
                                 'azalea_leaves', 'azalea_leaves_flowered',
                                 'mangrove_leaves', 'cherry_leaves', 'pale_oak_leaves'))

# Native cross plants can serialize correctly yet produce no visible faces.
# Keep each half independent so layer selection still works for tall plants.
PLANT_PROXIES = {
    ('minecraft:short_grass', 0): 'modern_projection:preview_short_grass',
    ('minecraft:fern', 0): 'modern_projection:preview_fern',
    ('minecraft:tall_grass', 0): 'modern_projection:preview_tall_grass_bottom',
    ('minecraft:tall_grass', 1): 'modern_projection:preview_tall_grass_top',
    ('minecraft:large_fern', 0): 'modern_projection:preview_large_fern_bottom',
    ('minecraft:large_fern', 1): 'modern_projection:preview_large_fern_top',
}

# The engine can return item metadata for hidden custom blocks despite
# register_to_creative_menu=false. Keep render-only IDs out of the picker.
INTERNAL_RENDER_BLOCKS = frozenset(list(LEAF_PROXIES.values()) + list(PLANT_PROXIES.values()) +
                                 ['modern_projection:preview_grid', 'modern_projection:preview_outline'])


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
        if value == AIR:
            continue
        entries.setdefault(value, []).append(index)
    for value in set(changes.values()):
        if value == AIR:
            continue
        if value[0] == 'minecraft:snow_layer':
            record = states(value)
        elif value in other_records:
            record = other_records[value]
        else:
            record = states(value)
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


def _normalize_native_layers(common, common_states, extra, extra_states):
    # Logical layers remain untouched. Native tessellation needs standalone
    # background blocks in common, and snow before its covered plant.
    if not extra:
        for value, positions in list(common.items()):
            if value[0] != 'minecraft:snow_layer':
                continue
            replacement = _covered_snow(value, False)
            if replacement != value:
                common.pop(value)
                common.setdefault(replacement, []).extend(positions)
                common_states[replacement] = states(replacement)
        return
    if not any(value[0] == 'minecraft:snow_layer' for value in list(common) + list(extra)):
        _promote_standalone(common, common_states, extra, extra_states)
        return
    variants = {}

    def snow(value, covered):
        key = (value, covered)
        if key not in variants:
            variants[key] = _covered_snow(value, covered)
        return variants[key]

    backs = dict((index, value) for value, positions in extra.items()
                 if value != AIR for index in positions)
    fronts = {}
    if backs:
        fronts = dict((index, value) for value, positions in common.items()
                      if value != AIR for index in positions if index in backs)
    front_changes, back_changes = {}, {}
    for index, back in backs.items():
        front = fronts.get(index, AIR)
        if front == AIR:
            front_changes[index] = (snow(back, False)
                                    if back[0] == 'minecraft:snow_layer' else back)
            back_changes[index] = AIR
        elif back[0] == 'minecraft:snow_layer' and is_snow_coverable(front):
            front_changes[index] = snow(back, True)
            back_changes[index] = front
    for front, positions in common.items():
        if front[0] != 'minecraft:snow_layer':
            continue
        for index in positions:
            replacement = snow(front, is_snow_coverable(backs.get(index, AIR)))
            if replacement != front:
                front_changes[index] = replacement
    old_common_states = dict(common_states)
    _replace_positions(common, common_states, front_changes, extra_states)
    _replace_positions(extra, extra_states, back_changes, old_common_states)


def _proxy_foreground(entries, records):
    result, state_records = {}, {}
    for value, positions in entries.items():
        proxy = LEAF_PROXIES.get(value[0]) or PLANT_PROXIES.get(value)
        rendered = (proxy, 0) if proxy is not None else value
        result.setdefault(rendered, []).extend(positions)
        record = states(rendered) if proxy is not None else records.get(value)
        if record is not None and (proxy is None or record):
            state_records[rendered] = record
    return result, state_records


def prepare_palette(source):
    """Copy and canonicalize both native layers and actor payloads."""
    data = dict(source)

    def prepare_layer(key):
        entries, records = {}, {}
        supplied = source.get('states' if key == 'common' else 'extraStates', {})
        supplied = dict((canonical(value), dict(record))
                        for value, record in supplied.items())
        for original, positions in source.get(key, {}).items():
            value = canonical(original)
            entries.setdefault(value, []).extend(positions)
            record = supplied.get(canonical(original))
            record = states(value) if record is None else record
            if record is not None:
                records[value] = record
        for positions in entries.values():
            positions.sort()
        return entries, records

    common, common_states = prepare_layer('common')
    extra, extra_states = prepare_layer('extra')
    _normalize_native_layers(common, common_states, extra, extra_states)
    common, common_states = _proxy_foreground(common, common_states)
    for entries in (common, extra):
        for positions in entries.values():
            positions.sort()
    extra_states = dict((value, record) for value, record in extra_states.items()
                        if value in extra)
    actors = {}
    for name, entries in source.get('actor', {}).items():
        rendered = {}
        for index, payload in entries.items():
            actor = render_actor(payload)
            if actor is not None:
                rendered[index] = actor
        if rendered:
            actors[name] = rendered
    data.update(common=common, states=common_states, extra=extra,
                extraStates=extra_states, actor=actors)
    return data
