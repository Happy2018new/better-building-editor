"""Versioned flat-family resources with independent UI/world calibration gates."""
from . import block_registry
from . import item_sprite_data as source
from .item_sprite_plan import PAYLOAD_VERSION


class ItemSpriteProfile(object):
    def __init__(self):
        if (source.SCHEMA_VERSION != 1 or source.PAYLOAD_VERSION != PAYLOAD_VERSION or
                source.SOURCE_VERSION != block_registry.source_version() or
                source.PALETTE_SHA256 != block_registry.fingerprint()):
            raise ValueError('Item sprite resources need regeneration for this block registry')
        self.items = source.ITEMS
        self.max_groups = source.MAX_GROUPS
        self.world_scale, self.world_rotation = (16.,) * 3, (0.,) * 3

    @staticmethod
    def ui_pose(unit, pitch, yaw, size):
        return unit / min(size), pitch - 90., 0., yaw

    @staticmethod
    def ui_offset(size):
        return 0., min(size) / 4.


def candidate_profile():
    return ItemSpriteProfile()


def production_profile():
    if not source.PRODUCTION_QUALIFIED:
        return None
    digest = source.QUALIFICATION_SHA256
    if (not isinstance(digest, str) or len(digest) != 64 or
            any(value not in '0123456789abcdef' for value in digest)):
        raise ValueError('Item sprite deployment requires its visible acceptance fingerprint')
    if source.QUALIFICATION_RESOURCE_SHA256 != source.RESOURCE_SHA256:
        raise ValueError('Item sprite qualification belongs to a different resource contract')
    return candidate_profile()
