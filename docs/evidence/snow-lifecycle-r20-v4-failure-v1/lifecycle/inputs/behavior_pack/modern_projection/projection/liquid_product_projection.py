"""Water-specific policy injection without changing other surface owners."""
from .liquid_projection import LiquidProjection
from .liquid_product_render import ProductWorldLiquidRenderer


class ProductLiquidProjection(LiquidProjection):
    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None,
                 renderer_factory=None, plan_factory=None):
        factory = renderer_factory if renderer_factory is not None else getattr(
            profile, 'renderer_factory', ProductWorldLiquidRenderer)
        LiquidProjection.__init__(self, bridge, document, origin, profile, dimension,
                                  hidden, layer, factory, plan_factory)
