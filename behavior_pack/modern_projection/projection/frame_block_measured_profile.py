"""Exact measured cube admission; ordinary items and artificial glint qualify separately."""
from . import block_registry
from . import frame_block_measured_data as source

ITEMS = frozenset((('minecraft:stone', 0), ('minecraft:quartz_block', 0),
                   ('minecraft:grass_block', 0)))
FRAME_NAMES = ('minecraft:frame',)
FRAME_POSES = frozenset(((2, 0),))


def candidate_items(engine_version):
    if (source.SCHEMA_VERSION != 1 or source.LAYOUT_VERSION != 1 or
            source.ENGINE_VERSION != engine_version or source.PALETTE_SHA256 != block_registry.fingerprint() or
            set(source.ITEMS) != ITEMS):
        raise ValueError('Measured cubes require their exact engine, palette and three item pairs')
    for key, row in source.ITEMS.items():
        if (row.get('material') != 'opaque' or row.get('family') != 'frame_block_cube' or
                row.get('content_families') != ('frame',) or row.get('supports_enchantment') is not True or
                row.get('observed_aux') != (0,) or row.get('resource_key') != key or
                not row['ui_model'].startswith('modern_projection_measured_frame_block_')):
            raise ValueError('Measured cube profile exceeds its native pair and material scope')
    return dict(source.ITEMS)


def production_items(engine_version):
    if engine_version != source.ENGINE_VERSION or not source.PRODUCTION_QUALIFIED:
        return {}
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest) or
            source.QUALIFICATION_RESOURCE_SHA256 != source.RESOURCE_SHA256 or
            source.POSE.get('accepted') is not True or not source.QUALIFIED_ITEMS or
            not set(source.QUALIFIED_ITEMS) <= ITEMS or
            not set(source.QUALIFIED_ENCHANTMENTS) <= set(source.QUALIFIED_ITEMS)):
        raise ValueError('Measured cube deployment needs exact resource and pair acceptance')
    candidates = candidate_items(engine_version)
    poses = source.QUALIFIED_FRAME_POSES
    if set(poses) != set(source.QUALIFIED_ITEMS):
        raise ValueError('Each measured item needs its explicit accepted frame poses')
    result = {}
    for key in source.QUALIFIED_ITEMS:
        accepted = poses[key]
        if (not isinstance(accepted, tuple) or not accepted or
                any(not isinstance(pose, tuple) or len(pose) != 2 or
                    any(type(axis) is not int for axis in pose) for pose in accepted) or
                not set(accepted) <= FRAME_POSES):
            raise ValueError('Measured frame deployment exceeds the tested north rotation-zero scope')
        row = dict(candidates[key])
        row['enchantment_qualified'] = key in source.QUALIFIED_ENCHANTMENTS
        row['frame_names'] = FRAME_NAMES
        row['frame_poses'] = frozenset(accepted)
        result[key] = row
    return result
