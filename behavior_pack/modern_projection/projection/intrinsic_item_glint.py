"""Native UI-confirmed inherent item glint, independent of actual enchantments."""

# R21 strict native UI census confirms each of these measured auxiliary values.
CONFIRMED_PAIRS = frozenset((name, aux) for name in (
    'minecraft:enchanted_golden_apple', 'minecraft:nether_star',
    'minecraft:end_crystal', 'minecraft:lodestone_compass',
    'minecraft:enchanted_book', 'minecraft:written_book', 'minecraft:experience_bottle',
    'minecraft:debug_stick') for aux in range(16))


def item_glint(item):
    name = item['newItemName']
    if isinstance(name, bytes):
        name = name.decode('utf8')
    return bool(item['isEnchanted'] or (name, item['newAuxValue']) in CONFIRMED_PAIRS)
