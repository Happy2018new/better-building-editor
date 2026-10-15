"""End portal world surfaces share existing publication and cleanup contracts."""
from .liquid_projection import LiquidProjection
from .portal_render_plan import iter_render_steps


def projection_plan(document, profile, targets, visible, opacity):
    return iter_render_steps(document, profile, targets, visible, True, opacity)


class PortalProjection(LiquidProjection):
    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None):
        LiquidProjection.__init__(self, bridge, document, origin, profile, dimension,
                                  hidden, layer, plan_factory=projection_plan)
