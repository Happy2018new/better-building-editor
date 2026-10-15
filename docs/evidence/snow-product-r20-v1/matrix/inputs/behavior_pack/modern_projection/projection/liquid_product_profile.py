"""Compose a declared water style independently of exact native qualification."""
from . import block_registry, liquid_face_texture_data, liquid_render_target_data
from .liquid_face_textures import LiquidFaceTextures
from .liquid_profile import _models, _side_templates, _text, _uv_rotations, _vector
from .liquid_render_plan import WATER_NAMES
from .liquid_product_render import ProductWorldLiquidRenderer
from .liquid_product_projection import ProductLiquidProjection
from .liquid_transport import PAYLOAD_VERSION
from .storage import integer_types


class ProductLiquidProfile(object):
    """SDK-free resource adapter over a complete immutable document snapshot."""
    renderer_factory = ProductWorldLiquidRenderer
    projection_factory = ProductLiquidProjection

    def __init__(self, resources, ui_pose, ui_offset):
        liquid_render_target_data.check_version(block_registry.source_version(), block_registry.fingerprint())
        from . import liquid_product_shape_data as rules
        from .liquid_native_shapes import product_check_version
        product_check_version()
        if (not isinstance(resources, dict) or resources.get('schema_version') != 2
                or resources.get('payload_version') != PAYLOAD_VERSION
                or resources.get('game_version') != block_registry.source_version()
                or not _text(resources.get('palette_sha256'))
                or resources.get('palette_sha256', '').lower() != block_registry.fingerprint().lower()
                or resources.get('product_style_version') != rules.PRODUCT_STYLE_VERSION
                or resources.get('face_texture_rows_sha256') != liquid_face_texture_data.RESOURCE_ROWS_SHA256):
            raise ValueError('Product water resources need regeneration for this registry and style')
        if not callable(ui_pose) or not callable(ui_offset):
            raise ValueError('Product water needs explicit calibrated UI transforms')
        self.models, self.world_models = _models(resources.get('models'))
        self.uv_rotations = _uv_rotations(resources.get('uv_rotations'), self.models)
        self.side_templates = _side_templates(resources.get('side_templates'), self.models, self.uv_rotations)
        self.top_templates = dict(resources.get('top_templates', {}))
        template = rules.TOP_TEMPLATE
        if (self.top_templates != {'flowing_water_grey': template}
                or self.uv_rotations.get(('flowing_water_grey', template)) != frozenset(range(256))
                or any(uv[0] == template for uv in self.side_templates.values())):
            raise ValueError('Product flowing tops need a separate template and all direction codes')
        names = resources.get('supported_names')
        if (not isinstance(names, (tuple, list)) or not names
                or any(not _text(name) for name in names) or len(set(names)) != len(names)
                or not set(names).issubset(WATER_NAMES & frozenset(rules.SUPPORTED_NAMES))):
            raise ValueError('Product water must declare names covered by its shape rules')
        self.supported_names = frozenset(names)
        for name in self.supported_names:
            top, bottom, side = liquid_face_texture_data.FACE_TEXTURES[name]
            if ((top, None) not in self.models or (bottom, None) not in self.models
                    or side not in self.side_templates):
                raise ValueError('Product resources do not cover their water face textures')
        budget = resources.get('max_groups')
        if isinstance(budget, bool) or not isinstance(budget, integer_types) or budget < 1:
            raise ValueError('Product water needs a positive model budget')
        self.max_groups = budget
        self.world_scale = _vector(resources.get('world_scale'), positive=True)
        self.world_rotation = _vector(resources.get('world_rotation'))
        self.ui_pose, self.ui_offset = ui_pose, ui_offset
        self.style_version, self.rules_sha256 = rules.PRODUCT_STYLE_VERSION, rules.PRODUCT_RULES_SHA256

    def provider_factory(self, document):
        from .liquid_native_shapes import product_shape_provider
        provider = LiquidFaceTextures(product_shape_provider(document, self.supported_names),
                                      self.side_templates, self.uv_rotations, self.top_templates)
        provider.coalesce_coincident_layers = True
        return provider
