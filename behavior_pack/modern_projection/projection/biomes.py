# -*- coding: utf-8 -*-
"""Building-local biome tint presets; never changes the world's biomes."""
from __future__ import unicode_literals

# Stable shader indices. Colors sampled from the 3.9 vanilla grass/foliage
# colormaps at each biome's temperature and temperature * rainfall.
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
)
KEYS = tuple(row[0] for row in PRESETS)
DEFAULT = 'plains'

# Explicit matches from vanilla climate definitions. Do not strip suffixes:
# e.g. birch_forest_hills_mutated uses forest's climate, while jungle_edge
# and jungle have different rainfall; pale_garden also has a color override.
NATIVE_ALIASES = dict((alias, key) for key, aliases in (
    ('plains', ('sunflower_plains', 'beach', 'deep_dark')),
    ('forest', ('forest_hills', 'flower_forest', 'birch_forest_hills_mutated')),
    ('birch_forest', ('birch_forest_hills', 'birch_forest_mutated')),
    ('taiga', ('taiga_hills', 'taiga_mutated', 'redwood_taiga_mutated',
               'mega_taiga', 'mega_taiga_hills', 'redwood_taiga_hills_mutated')),
    ('jungle', ('jungle_hills', 'jungle_mutated', 'bamboo_jungle', 'bamboo_jungle_hills')),
    ('desert', ('desert_hills', 'desert_mutated')),
    ('savanna', ('savanna_mutated', 'savanna_plateau')),
    ('ice_plains', ('cold_taiga', 'cold_taiga_hills', 'cold_taiga_mutated',
                    'ice_mountains', 'ice_plains_spikes', 'frozen_river',
                    'frozen_ocean', 'legacy_frozen_ocean', 'frozen_peaks',
                    'jagged_peaks', 'grove', 'snowy_slopes')),
) for alias in aliases)


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
    return NATIVE_ALIASES.get(key)


def actor_uniform(value):
    return (19487., float(shader_index(value)), 0., 0.)
