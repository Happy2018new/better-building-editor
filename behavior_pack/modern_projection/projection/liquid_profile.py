"""Compose versioned liquid rules and native resources for UI and world owners."""
import math

from . import block_registry, liquid_face_texture_data, liquid_shape_data
from .cell import text_type
from .liquid_face_textures import LiquidFaceTextures
from .liquid_native_shapes import check_version, shape_provider
from .liquid_render_plan import TEXTURES, WATER_NAMES, LAVA_NAMES
from .liquid_transport import PAYLOAD_VERSION
from .storage import integer_types


def _text(value):
    return isinstance(value, (bytes, text_type)) and 0 < len(value) <= 160


def _vector(value, positive=False):
    if (not isinstance(value, (tuple, list)) or len(value) != 3
            or any(isinstance(axis, bool) or not isinstance(axis, integer_types + (float,))
                   or math.isnan(axis) or math.isinf(axis) or positive and axis <= 0 for axis in value)):
        raise ValueError('Native liquid resources need explicit finite world scale and rotation')
    return tuple(value)


def _models(rows):
    if not isinstance(rows, (tuple, list)) or not rows:
        raise ValueError('Native liquid resources need explicit UI and world model rows')
    models, world_models, names = {}, {}, set()
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 4:
            raise ValueError('Liquid resource rows need texture, UV template, UI model and world model')
        texture, template, ui, world = row
        if (not _text(texture) or texture not in TEXTURES or template is not None and not _text(template)
                or texture.startswith('flowing_') and template is None
                or not _text(ui) or not _text(world) or ui == world):
            raise ValueError('Liquid model resources need separate UI/world names and explicit flowing UVs')
        key = texture, template
        if key in models:
            raise ValueError('Liquid resources repeat a texture/UV template')
        if ui in names or world in names:
            raise ValueError('Liquid resources repeat a UI or world model name')
        models[key], world_models[key] = ui, world
        names.update((ui, world))
    return models, world_models


def _uv_rotations(rows, models):
    if not isinstance(rows, (tuple, list)):
        raise ValueError('Native liquid resources need explicit model UV rotation capabilities')
    result = {}
    for row in rows:
        if not isinstance(row, (tuple, list)) or len(row) != 3:
            raise ValueError('Liquid UV capabilities need texture, template and allowed rotation codes')
        texture, template, codes = row
        if (not _text(texture) or template is not None and not _text(template)
                or not isinstance(codes, (tuple, list)) or not codes
                or any(isinstance(code, bool) or not isinstance(code, integer_types)
                       or not 0 <= code <= 255 for code in codes)):
            raise ValueError('Liquid UV capabilities need explicit eight-bit rotation codes')
        key = texture, template
        if key not in models or key in result or len(set(codes)) != len(codes):
            raise ValueError('Liquid UV capabilities repeat or name an unregistered model template')
        result[key] = frozenset(codes)
    if set(result) != set(models):
        raise ValueError('Liquid UV capabilities must cover every registered model template')
    return result


def _side_templates(values, models, uv_rotations):
    if not isinstance(values, dict):
        raise ValueError('Native liquid side UV templates must be explicit')
    result = {}
    for texture, uv in values.items():
        if (not _text(texture) or texture not in TEXTURES or not isinstance(uv, (tuple, list)) or len(uv) != 2
                or not _text(uv[0]) or isinstance(uv[1], bool)
                or not isinstance(uv[1], integer_types) or not 0 <= uv[1] <= 255
                or (texture, uv[0]) not in models):
            raise ValueError('Native liquid side UVs need registered model templates and rotation codes')
        if uv[1] not in uv_rotations[(texture, uv[0])]:
            raise ValueError('Native liquid side UV rotation is unsupported by its model resource')
        result[texture] = tuple(uv)
    return result


class NativeLiquidProfile(object):
    """Explicit deployment adapter; creating it does not accept native visuals.

    Resource data is a generated Python value, not an SDK-dependent import or
    runtime JSON read. Pose and screen offsets belong to the calibrated native
    adapter. The provider always consumes the unchanged complete document.
    """
    def __init__(self, resources, ui_pose, ui_offset, flow_uv=None):
        check_version()
        if (not isinstance(resources, dict) or resources.get('schema_version') != 2
                or resources.get('payload_version') != PAYLOAD_VERSION
                or resources.get('game_version') != block_registry.source_version()
                or not _text(resources.get('palette_sha256'))
                or resources.get('palette_sha256', '').lower() != block_registry.fingerprint().lower()
                or resources.get('shape_candidate_sha256') != liquid_shape_data.CANDIDATE_SHA256
                or resources.get('face_texture_rows_sha256') != liquid_face_texture_data.RESOURCE_ROWS_SHA256):
            raise ValueError('Native liquid resource profile needs regeneration for these shape/texture sources')
        if not callable(ui_pose) or not callable(ui_offset) or flow_uv is not None and not callable(flow_uv):
            raise ValueError('Native liquid profile needs explicit calibrated UI transforms')
        self.models, self.world_models = _models(resources.get('models'))
        self.uv_rotations = _uv_rotations(resources.get('uv_rotations'), self.models)
        self.side_templates = _side_templates(resources.get('side_templates'), self.models, self.uv_rotations)
        names = resources.get('supported_names', liquid_shape_data.SUPPORTED_NAMES)
        if (not isinstance(names, (tuple, list, set, frozenset)) or not names
                or any(not _text(name) for name in names)
                or len(set(names)) != len(names)
                or not set(names).issubset(WATER_NAMES | LAVA_NAMES)
                or any(('water' if name in WATER_NAMES else 'lava') not in liquid_shape_data.HEIGHT_RULES
                       for name in names)):
            raise ValueError('Native liquid profile needs explicit names covered by its shape rules')
        self.supported_names = frozenset(names)
        for name in self.supported_names:
            top, bottom, side = liquid_face_texture_data.FACE_TEXTURES[name]
            if ((top, None) not in self.models or (bottom, None) not in self.models
                    or side not in self.side_templates):
                raise ValueError('Liquid resources do not cover the supported native face textures')
        budget = resources.get('max_groups')
        if isinstance(budget, bool) or not isinstance(budget, integer_types) or budget < 1:
            raise ValueError('Native liquid resource profile needs a positive model budget')
        self.max_groups = budget
        self.world_scale = _vector(resources.get('world_scale'), positive=True)
        self.world_rotation = _vector(resources.get('world_rotation'))
        self.ui_pose, self.ui_offset, self.flow_uv = ui_pose, ui_offset, flow_uv

    def provider_factory(self, document):
        return LiquidFaceTextures(shape_provider(document, self.flow_uv, self.supported_names),
                                  self.side_templates, self.uv_rotations)
