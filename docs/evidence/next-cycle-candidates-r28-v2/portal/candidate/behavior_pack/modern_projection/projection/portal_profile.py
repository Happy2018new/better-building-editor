"""Version-scoped End portal surfaces; source blocks and NBT stay logical."""
from .cell import integer_types

ENGINE_VERSION = '3.10.0.420447'
SCHEMA_VERSION = 1
STYLE = 'native_artwork_layered_starfield_v1'
PORTAL_NAMES = frozenset(('minecraft:end_portal', 'minecraft:end_gateway'))
PREFIX = 'modern_projection_portal_'
PRODUCT_QUALIFIED = True
QUALIFICATION_SHA256 = '36ecdb6c95b5926a01e5e6ff4215881a85b2d261df1ea7059b1ea331c057e915'
NATIVE_PREFIX = 'modern_projection_portal_native_'
NATIVE_STYLE = 'native_ray_planes_candidate_r21'
NATIVE_PRODUCT_QUALIFIED = False
NATIVE_QUALIFICATION_SHA256 = ''
NATIVE_WORLD_STYLE = 'native_world_legacy_preview_r22'
NATIVE_WORLD_QUALIFICATIONS = {
    'end_gateway': {'qualified': False, 'sha256': ''},
    'end_portal': {'qualified': False, 'sha256': ''},
}


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

    @staticmethod
    def ui_offset_for_gui(size, gui):
        """Compensate the native skeleton anchor at the actual GUI scale."""
        if (isinstance(gui, bool) or not isinstance(gui, integer_types + (float,))
                or not 1. <= gui < float('inf') or gui != round(gui)):
            raise ValueError('Portal preview needs a positive integer native GUI scale')
        return 0., min(size) / float(gui)

    def __init__(self, max_groups=128, prefix=PREFIX, style=STYLE, world_prefix=None):
        if (type(max_groups) is bool or not isinstance(max_groups, integer_types) or
                max_groups < 1):
            raise ValueError('Portal surface profile needs a positive owned model budget')
        self.models = dict((name, prefix + name) for name in ('end_portal', 'end_gateway'))
        world_prefix = prefix if world_prefix is None else world_prefix
        self.world_models = dict((name, world_prefix + name + '_world') for name in self.models)
        self.max_groups = max_groups
        self.identity = (SCHEMA_VERSION, ENGINE_VERSION, style, max_groups)


def candidate_profile(max_groups=128):
    return PortalProfile(max_groups)


def native_candidate_profile(max_groups=128):
    return PortalProfile(max_groups, NATIVE_PREFIX, NATIVE_STYLE)


def native_world_candidate_profile(max_groups=128, families=('end_gateway',)):
    """Use measured native world surfaces while retaining the existing preview."""
    if (not families or len(set(families)) != len(families) or
            any(name not in ('end_gateway', 'end_portal') for name in families)):
        raise ValueError('Native world portal qualification needs explicit supported families')
    families = tuple(sorted(families))
    style = NATIVE_WORLD_STYLE + '_' + '_'.join(families)
    profile = PortalProfile(max_groups, PREFIX, style)
    for name in families:
        profile.world_models[name] = NATIVE_PREFIX + name + '_world'
    return profile


def native_world_production_profile(engine_version=None, max_groups=128):
    if engine_version != ENGINE_VERSION:
        return None
    families = []
    for name, row in sorted(NATIVE_WORLD_QUALIFICATIONS.items()):
        if name not in ('end_gateway', 'end_portal'):
            raise ValueError('Native world portal qualification has an unsupported family')
        if row['qualified'] is not True:
            continue
        digest = row['sha256']
        if len(digest) != 64 or any(value not in '0123456789abcdef' for value in digest):
            raise ValueError('Native world portal family needs its own visible qualification: ' + name)
        families.append(name)
    return native_world_candidate_profile(max_groups, families) if families else None


def native_production_profile(engine_version=None, max_groups=128):
    if engine_version != ENGINE_VERSION or NATIVE_PRODUCT_QUALIFIED is not True:
        return None
    if (len(NATIVE_QUALIFICATION_SHA256) != 64 or
            any(value not in '0123456789abcdef' for value in NATIVE_QUALIFICATION_SHA256)):
        raise ValueError('Native portal surfaces need their own visible qualification')
    return native_candidate_profile(max_groups)


def production_profile(engine_version=None, max_groups=128):
    if engine_version != ENGINE_VERSION or not PRODUCT_QUALIFIED:
        return None
    native = native_production_profile(engine_version, max_groups)
    if native is not None:
        return native
    native_world = native_world_production_profile(engine_version, max_groups)
    if native_world is not None:
        return native_world
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
