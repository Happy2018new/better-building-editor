# -*- coding: utf-8 -*-
"""Native render palettes; document and world block identities stay intact."""
from .block_registry import canonical, states


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
INTERNAL_RENDER_BLOCKS = frozenset(list(LEAF_PROXIES.values()) + list(PLANT_PROXIES.values()))


def prepare_palette(source):
    """Copy and canonicalize native render data without changing its owner."""
    data = dict(source)
    common = {}
    for value, positions in source['common'].items():
        value = canonical(value)
        proxy = LEAF_PROXIES.get(value[0]) or PLANT_PROXIES.get(value)
        if proxy is not None:
            value = (proxy, 0)
        common.setdefault(value, []).extend(positions)
    records = {}
    for value, positions in common.items():
        # Equivalent leaf lifecycle flags and legacy names reuse one geometry.
        positions.sort()
        record = states(value)
        if record is not None:
            # Empty records matter for native split blocks, e.g. colored glass.
            records[value] = record
    data['common'], data['states'] = common, records
    return data
