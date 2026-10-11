"""Compose versioned liquid rules and native resources for UI and world owners."""
import math

from . import block_registry, liquid_face_texture_data, liquid_shape_data
from .cell import text_type
from .liquid_face_textures import LiquidFaceTextures
from .liquid_native_shapes import check_version, shape_provider
from .liquid_render_plan import TEXTURES
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
    models, world_models = {}, {}
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
        models[key], world_models[key] = ui, world
    return models, world_models


def _side_templates(values, models):
    if not isinstance(values, dict):
        raise ValueError('Native liquid side UV templates must be explicit')
    result = {}
    for texture, uv in values.items():
        if (not _text(texture) or texture not in TEXTURES or not isinstance(uv, (tuple, list)) or len(uv) != 2
                or not _text(uv[0]) or isinstance(uv[1], bool)
                or not isinstance(uv[1], integer_types) or not 0 <= uv[1] <= 255
                or (texture, uv[0]) not in models):
            raise ValueError('Native liquid side UVs need registered model templates and rotation codes')
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
        if (not isinstance(resources, dict) or resources.get('schema_version') != 1
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
        self.side_templates = _side_templates(resources.get('side_templates'), self.models)
        for name in liquid_shape_data.SUPPORTED_NAMES:
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
        return LiquidFaceTextures(shape_provider(document, self.flow_uv), self.side_templates)
