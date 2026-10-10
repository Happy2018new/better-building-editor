# -*- coding: utf-8 -*-
"""Native entity fixtures with versioned observed default payloads."""
from __future__ import unicode_literals
from . import block_registry as registry
from .debug_blueprints import material, tag
from .debug_entity_defaults import evidence, material as native_material, nbt as native_nbt
from .nbt_spatial import root_payload, set_scalar

SCHEMA_VERSION = 1
# Each tuple is a test association, not an engine entity capability allowlist.
ENTITY_CASES = (
    ('classic', 'Furnace', 'furnace'), ('classic', 'Chest', 'chest'),
    ('classic', 'NetherReactor', 'netherreactor'), ('classic', 'Sign', 'standing_sign'),
    ('classic', 'MobSpawner', 'mob_spawner'), ('classic', 'Skull', 'skeleton_skull'),
    ('classic', 'FlowerPot', 'flower_pot'), ('classic', 'BrewingStand', 'brewing_stand'),
    ('classic', 'EnchantTable', 'enchanting_table'), ('classic', 'DaylightDetector', 'daylight_detector'),
    ('classic', 'Music', 'noteblock'), ('classic', 'Comparator', 'unpowered_comparator'),
    ('classic', 'Dispenser', 'dispenser'), ('classic', 'Dropper', 'dropper'),
    ('classic', 'Hopper', 'hopper'), ('classic', 'Cauldron', 'cauldron'),
    ('classic', 'ItemFrame', 'frame'), ('classic', 'PistonArm', 'piston'),
    ('classic', 'MovingBlock', 'moving_block'), ('classic', 'Beacon', 'beacon'),
    ('classic', 'EndPortal', 'end_portal'), ('classic', 'EnderChest', 'ender_chest'),
    ('classic', 'EndGateway', 'end_gateway'), ('classic', 'ShulkerBox', 'purple_shulker_box'),
    ('classic', 'CommandBlock', 'command_block'), ('classic', 'Bed', 'bed'),
    ('classic', 'Banner', 'standing_banner'),
    ('mechanisms', 'StructureBlock', 'structure_block'), ('mechanisms', 'Jukebox', 'jukebox'),
    ('mechanisms', 'ChemistryTable', 'compound_creator'), ('mechanisms', 'Conduit', 'conduit'),
    ('mechanisms', 'JigsawBlock', 'jigsaw'), ('mechanisms', 'Lectern', 'lectern'),
    ('mechanisms', 'BlastFurnace', 'blast_furnace'), ('mechanisms', 'Smoker', 'smoker'),
    ('mechanisms', 'Bell', 'bell'), ('mechanisms', 'Campfire', 'campfire'),
    ('mechanisms', 'Barrel', 'barrel'), ('mechanisms', 'Beehive', 'beehive'),
    ('mechanisms', 'Lodestone', 'lodestone'), ('mechanisms', 'CraftingTable', 'crafting_table'),
    ('recent', 'SculkSensor', 'sculk_sensor'), ('recent', 'SporeBlossom', 'spore_blossom'),
    ('recent', 'GlowItemFrame', 'glow_frame'), ('recent', 'SculkCatalyst', 'sculk_catalyst'),
    ('recent', 'SculkShrieker', 'sculk_shrieker'), ('recent', 'HangingSign', 'oak_hanging_sign'),
    ('recent', 'ChiseledBookshelf', 'chiseled_bookshelf'), ('recent', 'BrushableBlock', 'suspicious_sand'),
    ('recent', 'DecoratedPot', 'decorated_pot'), ('recent', 'CalibratedSculkSensor', 'calibrated_sculk_sensor'),
    ('recent', 'Crafter', 'crafter'), ('recent', 'TrialSpawner', 'trial_spawner'),
    ('recent', 'Vault', 'vault'), ('recent', 'CreakingHeart', 'creaking_heart'),
    ('recent', 'Shelf', 'oak_shelf'), ('recent', 'CopperGolemStatue', 'copper_golem_statue'),
)
REFERENCE_EXCLUSIONS = (
    ('NeteaseContainer', 'No confirmed standalone native fixture block.'),
    ('ModBlock', 'Requires a real registered custom block definition.'),
)


def coverage():
    present, unavailable, native_unobserved = [], [], []
    for group, entity, name in ENTITY_CASES:
        record = {'group': group, 'entity': entity, 'block': 'minecraft:' + name}
        (present if record['block'] in registry.BLOCKS else unavailable).append(record)
        if record['block'] in registry.BLOCKS and native_material(record['block']) is None:
            native_unobserved.append(record)
    return {'schema_version': SCHEMA_VERSION, 'registry_version': registry.source_version(),
            'present': present, 'unavailable': unavailable,
            'native_unobserved': native_unobserved, 'native_evidence': evidence(),
            'reference_exclusions': list(REFERENCE_EXCLUSIONS),
            'payload_kind': 'native tagged default payloads, rebased to fixture coordinates'}


def populate(fixture, identity):
    group = identity.rsplit('.', 1)[-1]
    fixture.floor()
    columns = 6 if group == 'classic' else 5
    index = 0
    for category, entity, name in ENTITY_CASES:
        if category != group or 'minecraft:' + name not in registry.BLOCKS:
            continue
        pos = (3 + (index % columns) * 6, 1, 3 + (index // columns) * 6)
        index += 1
        fixture.plinth(pos, 'cyan_concrete' if index % 2 else 'magenta_concrete')
        render, fields = {}, {}
        if entity == 'ShulkerBox':
            render, fields = {'facingDirection': 1}, {'facing': tag(1, 1)}
        if entity in ('Sign', 'HangingSign'):
            render = {'signRealText': 'NBT', 'signColor': -16711936, 'signGlowing': True}
            front = root_payload(native_nbt('minecraft:' + name, pos))['FrontText']
            for field, value in (('Text', 'NBT'), ('FilteredText', 'NBT'),
                                 ('SignTextColor', -16711936), ('IgnoreLighting', 1)):
                set_scalar(front, field, value)
            fields['FrontText'] = front
            if entity == 'Sign':
                render['signStandingRotation'] = 0
        value = native_material('minecraft:' + name) or material(name)
        fixture.put(pos, value, entity=entity, render=render, fields=fields)
        if entity == 'Bed':
            from .block_groups import group_partner
            offset, reciprocal = group_partner(value)
            partner = tuple(pos[axis] + offset[axis] for axis in range(3))
            fixture.put(partner, reciprocal, entity=entity)
    return fixture.finish()
