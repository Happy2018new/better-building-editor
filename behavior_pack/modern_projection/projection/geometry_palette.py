# -*- coding: utf-8 -*-
"""Native render palettes; document and world block identities stay intact."""
from .block_registry import canonical, states
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


def prepare_palette(source):
    """Copy and canonicalize both native layers and actor payloads."""
    data = dict(source)

    def prepare_layer(key, proxy_blocks=False):
        entries, records = {}, {}
        supplied = source.get('states' if key == 'common' else 'extraStates', {})
        supplied = dict((canonical(value), dict(record))
                        for value, record in supplied.items())
        for original, positions in source.get(key, {}).items():
            value = canonical(original)
            proxy = (LEAF_PROXIES.get(value[0]) or PLANT_PROXIES.get(value)
                     if proxy_blocks else None)
            if proxy is not None:
                value = (proxy, 0)
            entries.setdefault(value, []).extend(positions)
            record = supplied.get(canonical(original))
            if proxy is None:
                record = states(value) if record is None else record
            else:
                record = states(value)
            if record is not None and (proxy is None or record):
                records[value] = record
        for positions in entries.values():
            positions.sort()
        return entries, records

    common, common_states = prepare_layer('common', True)
    extra, extra_states = prepare_layer('extra')
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
