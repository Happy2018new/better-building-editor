"""Version-scoped End portal surfaces; source blocks and NBT stay logical."""
from .cell import integer_types

ENGINE_VERSION = '3.10.0.420447'
SCHEMA_VERSION = 1
STYLE = 'native_artwork_layered_starfield_v1'
PORTAL_NAMES = frozenset(('minecraft:end_portal', 'minecraft:end_gateway'))
PREFIX = 'modern_projection_portal_'
PRODUCT_QUALIFIED = True
QUALIFICATION_SHA256 = '6bd90bcf26f753c52156f24d51632187db8c6271b1976a7631d6beb46a62240e'


class PortalProfile(object):
    supported_names = PORTAL_NAMES
    world_scale = (16., 16., 16.)
    world_rotation = (0., 0., 0.)

    @staticmethod
    def ui_pose(unit, pitch, yaw, size):
        return unit / min(size), pitch - 90., 0., yaw

    @staticmethod
    def ui_offset(size):
        return 0., min(size) / 4.

    def __init__(self, max_groups=128):
        if (type(max_groups) is bool or not isinstance(max_groups, integer_types) or
                max_groups < 1):
            raise ValueError('Portal surface profile needs a positive owned model budget')
        self.models = dict((name, PREFIX + name) for name in ('end_portal', 'end_gateway'))
        self.world_models = dict((name, PREFIX + name + '_world') for name in self.models)
        self.max_groups = max_groups
        self.identity = (SCHEMA_VERSION, ENGINE_VERSION, STYLE, max_groups)


def candidate_profile(max_groups=128):
    return PortalProfile(max_groups)


def production_profile(engine_version=None, max_groups=128):
    if engine_version != ENGINE_VERSION or not PRODUCT_QUALIFIED:
        return None
    if (len(QUALIFICATION_SHA256) != 64 or
            any(value not in '0123456789abcdef' for value in QUALIFICATION_SHA256)):
        raise ValueError('Portal surfaces need visible qualification for their engine bundle')
    return candidate_profile(max_groups)


def suppress(entries, records, profile):
    """Filter only detached draw maps; never remove source cell or actor data."""
    names = frozenset(getattr(profile, 'supported_names', ())) & PORTAL_NAMES
    if not names:
        return entries, records
    entries = dict((material, indices) for material, indices in entries.items()
                   if material[0] not in names)
    return entries, dict((material, record) for material, record in records.items()
                         if material in entries)
