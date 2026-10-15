"""Versioned cauldron appearances from the measured native 3.10 fixture."""
from .cauldron_appearance import decode_cauldron_appearance
from . import biomes
from .cauldron_render_plan import CauldronTop
from .cell import integer_types
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

ENGINE_VERSION = '3.10.0.420447'
PREFIX = 'modern_projection_cauldron_'


def _rgb(value):
    if (not isinstance(value, (tuple, list)) or len(value) != 3 or
            any(type(channel) is bool or not isinstance(channel, integer_types)
                or not 0 <= channel <= 255 for channel in value)):
        raise ValueError('Cauldron appearance requires measured RGB bytes')
    return tuple(value)


def _observed_actor(actor):
    if actor is None:
        return True
    root = root_payload(entity_nbt(actor))
    if not isinstance(root, dict) or scalar(root, 'id') not in ('Cauldron', b'Cauldron'):
        return False
    for name, kind in (('PotionId', 2), ('PotionType', 2), ('CustomColor', 3)):
        key = field_key(root, name)
        if key is None:
            continue
        tag = root[key]
        if not isinstance(tag, dict) or scalar(tag, '__type__') != kind:
            return False
        value = scalar(root, name)
        if type(value) is bool or not isinstance(value, integer_types):
            return False
    return True


class CauldronProfile(object):
    """Explicit candidate; selection belongs to the version/deployment adapter."""
    empty_shell = ('minecraft:cauldron', 0)
    empty_states = {'cauldron_liquid': 'water', 'fill_level': 0}
    world_scale = (16., 16., 16.)
    world_rotation = (0., 0., 0.)

    @staticmethod
    def ui_pose(unit, pitch, yaw, size):
        return unit / min(size), pitch - 90., 0., yaw

    @staticmethod
    def ui_offset(size):
        return 0., min(size) / 4.

    def __init__(self, data, max_groups=128):
        if (data.get('schema_version') != 1 or data.get('engine_version') != ENGINE_VERSION or
                data.get('geometry_measured') is not True or data.get('custom_rgb_measured') is not True):
            raise ValueError('Cauldron profile requires measured native 3.10 data')
        if type(max_groups) is bool or not isinstance(max_groups, integer_types) or max_groups < 1:
            raise ValueError('Cauldron profile requires a positive owned model budget')
        heights = tuple(data['heights'])
        if (len(heights) != 6 or any(type(height) is bool or not isinstance(height, (int, float))
                                  or not 0. < height < 1. for height in heights) or
                any(left >= right for left, right in zip(heights, heights[1:]))):
            raise ValueError('Cauldron profile requires six measured increasing fill heights')
        if data['inset'] != .125 or tuple(data['uv_bounds']) != (.125, .875):
            raise ValueError('Cauldron profile differs from the generated finite resource contract')
        self.heights = heights
        self.potions = dict((int(key), _rgb(value)) for key, value in data['potion_colors'].items())
        self.water = dict((name, _rgb(value)) for name, value in data['water_colors'].items())
        self.plain_water_style = data.get('plain_water_style')
        if self.plain_water_style not in (None, 'document_biome_world_water_v1'):
            raise ValueError('Unknown cauldron plain-water appearance style')
        self.snow = data.get('snow_geometry_measured') is True
        self.states = dict(((row['name'], row['aux']), dict(row['states'])) for row in data['states'])
        self.max_groups = max_groups
        self.models = dict((name, PREFIX+name) for name in ('water', 'plain_water', 'lava', 'snow'))
        self.world_models = dict((name, PREFIX+name+'_world') for name in ('water', 'plain_water', 'lava', 'snow'))
        self.identity = (1, ENGINE_VERSION, data['evidence_sha256'])

    def top(self, material, actor, biome):
        states = self.states.get(tuple(material))
        if states is None:
            return None
        appearance = decode_cauldron_appearance(material, states, actor)
        overlay = appearance.overlay
        if overlay.fill_level == 0:
            return None
        if overlay.liquid == 'powder_snow':
            return (CauldronTop(self.heights[overlay.fill_level-1], 'snow', (255,255,255), None)
                    if self.snow else None)
        if overlay.liquid == 'lava':
            return CauldronTop(self.heights[overlay.fill_level-1], 'lava', (255,255,255), None)
        if not _observed_actor(actor):
            return None
        if overlay.custom_color is not None:
            if not -2147483648 <= overlay.custom_color <= 2147483647:
                return None
            value = overlay.custom_color & 0xffffff
            color = ((value >> 16) & 255, (value >> 8) & 255, value & 255)
        elif overlay.potion_id in (None, -1) and overlay.potion_type in (None, -1):
            if self.plain_water_style == 'document_biome_world_water_v1':
                color, unused_opacity = biomes.water_appearance(biome)
                return CauldronTop(self.heights[overlay.fill_level-1], 'plain_water', color, None)
            color = self.water.get(biome)
        elif overlay.potion_type in (0, 1, 2):
            color = self.potions.get(overlay.potion_id)
        else:
            color = None
        if color is None:
            return None
        return CauldronTop(self.heights[overlay.fill_level-1], 'water', color, None)


def candidate_profile(max_groups=128):
    from .cauldron_native_data import DATA, SOURCE_SHA256
    profile = CauldronProfile(DATA, max_groups)
    profile.identity += (SOURCE_SHA256,)
    return profile
