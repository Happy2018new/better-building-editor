"""Book world companions retain logical targets, opacity and cleanup owners."""
from .liquid_projection import LiquidProjection
from .book_render_plan import iter_render_steps


def projection_plan(document,profile,targets,visible,opacity):
    return iter_render_steps(document,profile,targets,visible,True,opacity)


class BookProjection(LiquidProjection):
    def __init__(self,bridge,document,origin,profile,dimension,hidden=(),layer=None):
        LiquidProjection.__init__(self,bridge,document,origin,profile,dimension,
            hidden,layer,plan_factory=projection_plan)
