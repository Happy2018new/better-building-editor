# -*- coding: utf-8 -*-
"""Building-local biome tint presets; never changes the world's biomes."""
from __future__ import unicode_literals

# Stable shader indices: append new colors; do not reorder saved presets.
# Climate colors use the installed vanilla colormaps. Distinct appearance
# overrides are checked against the Bedrock 1.21.120 client biome resources.
# key, Chinese label, grass RGB, foliage RGB
PRESETS = (
    ('plains', '草原', '92BC58', '77AB2F'),
    ('forest', '森林', '79BF5A', '59AE30'),
    ('birch_forest', '白桦林', '88BA67', '6BA941'),
    ('taiga', '针叶林', '86B583', '68A464'),
    ('swampland', '沼泽', '4C763C', '6A7039'),
    ('mangrove_swamp', '红树林沼泽', '4C763C', '8DB127'),
    ('jungle', '丛林', '58CB3C', '30BB0B'),
    ('desert', '沙漠', 'BEB654', 'AEA42A'),
    ('savanna', '热带草原', 'BEB654', 'AEA42A'),
    ('ice_plains', '雪原', '80B496', '60A17B'),
    ('pale_garden', '苍白花园', '778272', '878D76'),
    ('cherry_grove', '樱花树林', 'B6DB61', 'B6DB61'),
    ('mesa', '恶地', '90814D', 'AEA42A'),
    ('roofed_forest', '黑森林', '507A32', '59AE30'),
)
KEYS = tuple(row[0] for row in PRESETS)
DEFAULT = 'plains'

# Desert and savanna share both colors. Keep their stored identifiers and
# shader indices compatible while presenting a single choice in the UI.
CHOICES = tuple((key, '干燥群系' if key == 'desert' else name, grass, foliage)
                for key, name, grass, foliage in PRESETS if key != 'savanna')

# Representative grass/foliage colors from installed 3.9.0.401155 vanilla
# biome climates, client-biome overrides, colormaps and grass-side atlas.
# Sample at (int((1-temperature)*255), int((1-temperature*downfall)*255))
# after clamping temperature/downfall to [0,1]. For grass_is_shaded use the
# native shaded grass swatch; ambient/world lighting is not sampled.
# Full variant names are intentional. This is a click-time preset lookup,
# not player-following tint or pixel mixing.
NATIVE_COLORS = dict((name, (grass, foliage)) for grass, foliage, names in (
    ('4C763C', '6A7039', 'swampland swampland_mutated'),
    ('4C763C', '8DB127', 'mangrove_swamp'),
    ('507A32', '59AE30', 'roofed_forest'),
    ('55CA3F', '2BBB0F', 'mushroom_island mushroom_island_shore'),
    ('58CB3C', '30BB0B', 'bamboo_jungle bamboo_jungle_hills jungle jungle_hills '
     'jungle_mutated'),
    ('64C83F', '3EB80F', 'jungle_edge jungle_edge_mutated'),
    ('778272', '878D76', 'pale_garden'),
    ('79BF5A', '59AE30', 'birch_forest_hills_mutated flower_forest forest forest_hills '
     'roofed_forest_mutated'),
    ('80B496', '60A17B', 'cold_taiga cold_taiga_hills cold_taiga_mutated frozen_ocean '
     'frozen_peaks frozen_river grove ice_mountains ice_plains '
     'ice_plains_spikes jagged_peaks legacy_frozen_ocean snowy_slopes'),
    ('82B493', '64A278', 'cold_beach'),
    ('82C343', '64B216', 'savanna_plateau_mutated'),
    ('86B583', '68A464', 'redwood_taiga_mutated taiga taiga_hills taiga_mutated'),
    ('86B67F', '68A55F', 'meadow mega_taiga mega_taiga_hills redwood_taiga_hills_mutated'),
    ('88BA67', '6BA941', 'birch_forest birch_forest_hills birch_forest_mutated'),
    ('8AB488', '6DA36B', 'extreme_hills extreme_hills_edge extreme_hills_mutated '
     'extreme_hills_plus_trees extreme_hills_plus_trees_mutated '
     'stone_beach'),
    ('8CB489', '70A26C', 'dripstone_caves'),
    ('8DB870', '71A74D', 'cold_ocean deep_cold_ocean deep_frozen_ocean deep_lukewarm_ocean '
     'deep_ocean deep_warm_ocean lukewarm_ocean ocean river the_end '
     'warm_ocean'),
    ('90814D', 'AEA42A', 'mesa mesa_bryce mesa_plateau_mutated mesa_plateau_stone '
     'mesa_plateau_stone_mutated'),
    ('92BC58', '77AB2F', 'beach deep_dark plains sunflower_plains'),
    ('9ABD4A', '82AC1E', 'stony_peaks'),
    ('B6DB61', 'B6DB61', 'cherry_grove'),
    ('B8B55B', 'A6A432', 'lush_caves'),
    ('BEB654', 'AEA42A', 'basalt_deltas crimson_forest desert desert_hills desert_mutated '
     'hell mesa_plateau savanna savanna_mutated savanna_plateau '
     'soulsand_valley warped_forest'),
) for name in names.split())


def _rgb(value):
    return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))


_PRESET_COLORS = tuple((key, _rgb(grass) + _rgb(foliage))
                       for key, unused, grass, foliage in PRESETS)


def nearest(grass, foliage, preferred=None):
    """Choose by grass/foliage RGB distance; a preferred name only breaks ties."""
    color = _rgb(grass) + _rgb(foliage)
    return min(_PRESET_COLORS,
               key=lambda row: (sum((a-b)*(a-b) for a, b in zip(color, row[1])),
                                row[0] != preferred))[0]


def validate(value):
    if isinstance(value, bytes):
        value = value.decode('utf8')
    if not isinstance(value, type('')) or value not in KEYS:
        raise ValueError('不支持的生物群系染色')
    return value


def shader_index(value):
    return KEYS.index(validate(value)) + 1


def label(value):
    return PRESETS[shader_index(value)-1][1]


def from_native(name):
    if isinstance(name, bytes):
        name = name.decode('utf8')
    if name and ':' in name and not name.startswith('minecraft:'):
        return None
    key = (name or '').split(':')[-1]
    if key in KEYS:
        return key
    color = NATIVE_COLORS.get(key)
    if color is None:
        return None
    # Desert/savanna colors are equal. Keep the familiar savanna label for
    # its variants only when it really is a nearest-color tie.
    preferred = 'savanna' if key.startswith('savanna_') else None
    return nearest(color[0], color[1], preferred)


def actor_uniform(value):
    return (19487., float(shader_index(value)), 0., 0.)
