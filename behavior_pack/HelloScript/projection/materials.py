# -*- coding: utf-8 -*-
"""Searchable block catalogue and ordered personal palette (no UI dependencies)."""
from __future__ import unicode_literals
import re
from .catalog import MATERIALS
DISPLAY_NAMES = dict((tuple(m[:2]), m[2]) for m in MATERIALS)

CATEGORIES = [('all', '全部方块', 'grid'), ('building', '建筑石材', 'cube'),
              ('wood', '木材', 'layers'), ('color', '彩色方块', 'brush'),
              ('nature', '自然', 'surface'), ('decor', '装饰照明', 'spark'),
              ('mechanism', '功能方块', 'sliders'), ('custom', '模组方块', 'plus')]
# Legacy identifiers still use aux values for distinct creative variants.
VARIANTS = {'stone': 7, 'dirt': 3, 'planks': 6, 'log': 4, 'log2': 2, 'leaves': 4,
            'leaves2': 2, 'wool': 16, 'concrete': 16, 'concrete_powder': 16,
            'stained_glass': 16, 'stained_glass_pane': 16, 'stained_hardened_clay': 16,
            'carpet': 16, 'sandstone': 3, 'red_sandstone': 3, 'quartz_block': 4,
            'stonebrick': 4, 'prismarine': 3, 'sand': 2, 'red_flower': 9,
            'sapling': 6, 'double_plant': 6, 'sponge': 2, 'stone_block_slab': 8,
            'stone_block_slab2': 8, 'stone_block_slab3': 8, 'stone_block_slab4': 5,
            'wooden_slab': 6}


def clean_name(value):
    if isinstance(value, bytes):
        value = value.decode('utf8')
    return re.sub('§.', '', value or '').strip()


def category(identifier, native_category='construction'):
    if not identifier.startswith('minecraft:'):
        return 'custom'
    word = identifier.split(':')[-1]
    if any(v in word for v in ('wool', 'concrete', 'stained', 'terracotta', 'carpet')):
        return 'color'
    if any(v in word for v in ('redstone', 'piston', 'hopper', 'dispenser', 'dropper', 'command',
                               'rail', 'observer', 'repeater', 'comparator', 'sculk', 'furnace',
                               'chest', 'crafting', 'anvil', 'enchant', 'barrel', 'button', 'pressure_plate')):
        return 'mechanism'
    if any(v in word for v in ('planks', 'log', 'wood', 'bamboo', 'oak', 'spruce', 'birch',
                               'acacia', 'jungle', 'mangrove', 'cherry', 'crimson', 'warped')) and not any(
            v in word for v in ('leaves', 'sapling', 'fungus', 'roots')):
        return 'wood'
    if any(v in word for v in ('glass', 'lantern', 'light', 'torch', 'glow', 'lamp', 'candle',
                               'bookshelf', 'flower_pot', 'banner', 'bed', 'chain')):
        return 'decor'
    return 'nature' if native_category == 'nature' else 'building'


def entry(identifier, aux, name, native_category='construction'):
    name = clean_name(name)
    DISPLAY_NAMES[(identifier, aux)] = name
    return {'value': (identifier, aux), 'name': name, 'category': category(identifier, native_category),
            'search': (name + ' ' + identifier).lower()}


def initial_catalogue():
    return [entry(m[0], m[1], m[2], 'nature' if m[0].endswith(('grass', 'leaves')) else 'construction') for m in MATERIALS]


def search_blocks(entries, group='all', query=''):
    words = clean_name(query).lower().split()
    return [item for item in entries if (group == 'all' or item['category'] == group) and
            all(word in item['search'] for word in words)]


def inventory_info(info):
    """Exclude untranslated/internal states without a creative inventory entry."""
    return bool(info and info.get('itemCategory') in ('construction','nature','items','equipment','custom') and
                clean_name(info.get('itemName')) and not clean_name(info['itemName']).startswith(('tile.','item.')))


def unique_inventory(entries, palette):
    # Split modern block IDs and legacy aux IDs can name the same creative
    # item. Prefer a saved shortcut, and show one tile per localized variant.
    chosen = {}
    for item in sorted(entries, key=lambda value: value['value']):
        key = (item['value'][0].split(':')[0], item['name'])
        if key not in chosen or item['value'] in palette:
            chosen[key] = item
    return sorted(chosen.values(), key=lambda item: (item['category'], item['name'], item['value']))


def normalize_palette(values):
    from .model import block
    result = []
    if not isinstance(values, (list, tuple)):
        values = [m[:2] for m in MATERIALS]
    for value in values[:64]:
        try:
            value = block(value)
        except (ValueError, TypeError, IndexError):
            continue
        if value not in result:
            result.append(value)
    return result
