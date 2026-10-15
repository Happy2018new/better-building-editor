"""Cauldron finite surfaces share world-liquid publication and cleanup."""
from .cauldron_render_plan import iter_render_steps
from .liquid_projection import LiquidProjection


def projection_plan(document, profile, targets, visible, opacity):
    return iter_render_steps(document, profile, targets, visible, True, opacity)


class CauldronProjection(LiquidProjection):
    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None):
        LiquidProjection.__init__(self, bridge, document, origin, profile, dimension,
                                  hidden, layer, plan_factory=projection_plan)
