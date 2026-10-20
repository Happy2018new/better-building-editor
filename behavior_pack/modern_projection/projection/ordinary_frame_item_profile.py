"""Eleven observed static aux-zero icons with explicit normal-frame pose admission."""
from . import block_registry
from . import item_icon_data as icons
from . import item_sprite_data as transport
from . import ordinary_frame_item_data as source

ITEMS = frozenset(('minecraft:' + name, 0) for name in (
    'iron_ingot', 'fishing_rod', 'diamond_pickaxe', 'diamond_sword', 'bow', 'bread',
    'bucket', 'bone', 'apple', 'bed', 'beef'))
ENCHANTMENTS = frozenset((('minecraft:diamond_sword', 0),))
FRAME_NAMES = ('minecraft:frame',)
FRAME_POSES = frozenset(((2, 0),))


def candidate_items(engine_version):
    if (source.SCHEMA_VERSION != 1 or icons.SCHEMA_VERSION != 1 or icons.LAYOUT_VERSION != 1 or
            engine_version != source.ENGINE_VERSION or engine_version != icons.ENGINE_VERSION or
            transport.PALETTE_SHA256 != block_registry.fingerprint()):
        raise ValueError('Ordinary frames need the exact measured engine, palette and icon layout')
    result = {}
    for key in ITEMS:
        row = dict(icons.ITEMS[key])
        if row.get('resource_key') != key or row.get('family') != 'flat_icon':
            raise ValueError('Ordinary frame baseline requires the observed static item resources')
        row.update(content_families=('frame',), observed_aux=(0,), max_durability=0,
                   frame_names=FRAME_NAMES, frame_poses=FRAME_POSES,
                   enchantment_qualified=key in ENCHANTMENTS)
        result[key] = row
    return result


def production_items(engine_version):
    if engine_version != source.ENGINE_VERSION or not source.PRODUCTION_QUALIFIED:
        return {}
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest) or
            source.QUALIFICATION_RESOURCE_SHA256 != icons.RESOURCE_SHA256 or
            not source.QUALIFIED_ITEMS or not set(source.QUALIFIED_ITEMS) <= ITEMS or
            not set(source.QUALIFIED_ENCHANTMENTS) <= ENCHANTMENTS & set(source.QUALIFIED_ITEMS) or
            set(source.QUALIFIED_FRAME_POSES) != set(source.QUALIFIED_ITEMS)):
        raise ValueError('Ordinary frame deployment needs its own exact pair, resource and pose acceptance')
    candidates = candidate_items(engine_version)
    result = {}
    for key in source.QUALIFIED_ITEMS:
        poses = source.QUALIFIED_FRAME_POSES[key]
        if (not isinstance(poses, tuple) or not poses or
                any(not isinstance(pose, tuple) or len(pose) != 2 or
                    any(type(axis) is not int for axis in pose) for pose in poses) or
                not set(poses) <= FRAME_POSES):
            raise ValueError('Ordinary frame acceptance exceeds the observed north rotation-zero scope')
        row = dict(candidates[key])
        row['frame_poses'] = frozenset(poses)
        row['enchantment_qualified'] = key in source.QUALIFIED_ENCHANTMENTS
        result[key] = row
    return result
