# -*- coding: utf-8 -*-
"""Native render palettes; document and world block identities stay intact."""
from .block_registry import canonical, states
from .native_layers import normalize_palette_layers
from .visible_actor import render_actor
from .entity_render import INTERNAL_BLOCKS, native_actor, prepare_static_entities
from .block_traits import is_snow_coverable
from .render_layout import MAX_LOGICAL_HEIGHT, OVERLAY_BASE
from .plant_proxy_data import STATIC_PLANT_PROXIES, STATIC_PLANT_MAX_Y


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
PLANT_PROXIES.update(STATIC_PLANT_PROXIES)

# The engine can return item metadata for hidden custom blocks despite
# register_to_creative_menu=false. Keep render-only IDs out of the picker.
INTERNAL_RENDER_BLOCKS = frozenset(list(LEAF_PROXIES.values()) + list(PLANT_PROXIES.values()) +
                                 list(INTERNAL_BLOCKS) +
                                 ['modern_projection:preview_grid', 'modern_projection:preview_outline'])


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


def _append_snow_overlays(common, common_states, extra, extra_states, volume, overlay_base):
    """Give native-ignored plants independent geometry in the same mesh."""
    snow_surfaces = {}
    for value, positions in common.items():
        if value[0] == 'minecraft:snow_layer':
            height = common_states.get(value, {}).get('height')
            if height is None:
                height = states(value)['height']
            surface = (height + 1) / 8.
            snow_surfaces.update((index, surface) for index in positions)
    if not snow_surfaces:
        return volume
    overlays = {}
    for value, positions in extra.items():
        if not is_snow_coverable(value):
            continue
        max_y = STATIC_PLANT_MAX_Y.get(value)
        # Native alpha bounds define complete burial, including exact surface equality.
        selected = [index for index in positions if index in snow_surfaces and
                    (max_y is None or snow_surfaces[index] < max_y)]
        if selected:
            overlays[value] = selected
    if not overlays:
        return volume
    if volume is None or len(volume) != 3 or not 0 < volume[2] <= MAX_LOGICAL_HEIGHT:
        raise ValueError('Snow overlay requires a supported native palette volume')
    if overlay_base <= volume[2]:
        raise ValueError('Snow overlay needs an empty cell above the native source volume')
    for value, positions in overlays.items():
        common.setdefault(value, []).extend(index + overlay_base * volume[0] * volume[1]
                                           for index in positions)
        record = extra_states.get(value)
        if record is not None:
            common_states[value] = record
    return (volume[0], volume[1], overlay_base + volume[2])


def prepare_palette(source, inferred_chest_parts=None, overlay_base=OVERLAY_BASE):
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
    normalize_palette_layers(common, common_states, extra, extra_states)
    volume = _append_snow_overlays(common, common_states, extra, extra_states,
                                  source.get('volume'), overlay_base)
    common, static_actors = prepare_static_entities(common, source.get('actor', {}), source.get('volume'),
                                                   inferred_chest_parts)
    common, common_states = _proxy_foreground(common, common_states)
    for entries in (common, extra):
        for positions in entries.values():
            positions.sort()
    extra_states = dict((value, record) for value, record in extra_states.items()
                        if value in extra)
    actors = {}
    materials = dict((index, value) for value, positions in common.items() for index in positions)
    for name, entries in source.get('actor', {}).items():
        normalized_name = name.decode('utf8') if isinstance(name, bytes) else name
        rendered = {}
        for index, payload in entries.items():
            if (normalized_name, index) in static_actors:
                continue
            material = materials.get(index)
            actor = native_actor(material, payload) if material is not None else render_actor(payload)
            if actor is not None:
                rendered[index] = actor
        if rendered:
            actors[name] = rendered
    data.update(common=common, states=common_states, extra=extra,
                extraStates=extra_states, actor=actors)
    if volume is not None:
        data['volume'] = volume
    return data
