"""Item payload adapters reuse the existing owned skeleton staging machinery."""
from .item_sprite_plan import WORLD_TAG, validate_uniforms, with_preview_distance
from .liquid_render import SkeletonLiquidRenderer, WorldLiquidRenderer, _finite_tuple
from .liquid_viewport import LiquidControls


class SkeletonItemRenderer(SkeletonLiquidRenderer):
    @staticmethod
    def validate(group, pose):
        validate_uniforms(group.uniforms)
        pose = _finite_tuple(pose, 4, 'item skeleton pose')
        if pose[0] <= 0.:
            raise ValueError('Item skeleton scale must be positive')
        return pose


class ItemControls(LiquidControls):
    def __init__(self, registry, model_component):
        LiquidControls.__init__(self, registry, model_component,
                                SkeletonItemRenderer, with_preview_distance)


class WorldItemRenderer(WorldLiquidRenderer):
    def __init__(self, bridge, max_groups, dimension, scale, rotation):
        WorldLiquidRenderer.__init__(self, bridge, max_groups, dimension, scale, rotation,
                                    validate_uniforms, WORLD_TAG)
