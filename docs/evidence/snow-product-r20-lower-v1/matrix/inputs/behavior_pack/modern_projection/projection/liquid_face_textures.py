"""Split native top, bottom and side materials without changing saved layers."""
from . import block_registry, liquid_face_texture_data as source, liquid_render_target_data
from .liquid_render_plan import LiquidSurface


class LiquidFaceTextures(object):
    """Decorate explicit shapes with versioned resources and caller-verified side UVs.

    The shape provider chooses the top texture/UV (including any flow direction).
    Native blocks.json supplies bottom and side resource keys; it cannot establish
    the side UV mapping or the choice of flowing top faces.
    """
    def __init__(self, provider, side_templates, uv_rotations=None, top_templates=None):
        liquid_render_target_data.check_version(block_registry.source_version(), block_registry.fingerprint())
        if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != block_registry.source_version()
                or source.PALETTE_SHA256.lower() != block_registry.fingerprint().lower()):
            raise ValueError('Native liquid face textures need regeneration for this registry')
        self.provider, self.side_templates = provider, dict(side_templates)
        self.top_templates = None if top_templates is None else dict(top_templates)
        self.uv_rotations = (None if uv_rotations is None else
                             dict((key, frozenset(codes)) for key, codes in uv_rotations.items()))

    def surface(self, document, pos, layer, value):
        shape = self.provider.surface(document, pos, layer, value)
        if not isinstance(shape, LiquidSurface):
            raise ValueError('Liquid face texture adapter needs a single complete input shape')
        textures = source.FACE_TEXTURES.get(value[0])
        if textures is None:
            raise ValueError('Native liquid face resources are unknown: ' + value[0])
        top, bottom, side = textures
        if shape.texture_key not in (top, side):
            raise ValueError('Liquid top resource differs from its native family')
        if self.top_templates is not None and shape.texture_key.startswith('flowing_'):
            if shape.flow_uv is None or shape.flow_uv[0] != self.top_templates.get(shape.texture_key):
                raise ValueError('Liquid flowing top needs its distinct registered top template')
        if self.uv_rotations is not None:
            template, rotation = (None, 0) if shape.flow_uv is None else shape.flow_uv
            if rotation not in self.uv_rotations.get((shape.texture_key, template), ()):
                raise ValueError('Liquid top UV template or rotation is unsupported by its model resource')
        materials, masks = [], {}
        for mask, texture, uv in ((1, shape.texture_key, shape.flow_uv),
                                  (32, bottom, None),
                                  (30, side, self.side_templates.get(side))):
            faces = shape.faces & mask
            if faces:
                resource = texture, uv
                if resource not in masks:
                    materials.append(resource)
                masks[resource] = masks.get(resource, 0) | faces
        # An explicit zero mask must survive the provider contract.
        return (tuple(LiquidSurface(pos, layer, shape.heights, masks[resource], *resource)
                      for resource in materials) if materials else shape)
