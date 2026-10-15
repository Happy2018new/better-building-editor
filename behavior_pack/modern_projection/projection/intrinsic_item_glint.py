"""Native UI-confirmed inherent item glint, independent of actual enchantments."""

# R21 paired native UI controls and purple temporal modulation confirm aux zero.
CONFIRMED_PAIRS = frozenset((name, 0) for name in (
    'minecraft:enchanted_golden_apple', 'minecraft:nether_star',
    'minecraft:end_crystal', 'minecraft:lodestone_compass',
    'minecraft:enchanted_book', 'minecraft:written_book', 'minecraft:experience_bottle'))


def item_glint(item):
    name = item['newItemName']
    if isinstance(name, bytes):
        name = name.decode('utf8')
    return bool(item['isEnchanted'] or (name, item['newAuxValue']) in CONFIRMED_PAIRS)
