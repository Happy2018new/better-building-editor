"""Private world item plans participate in the existing publication transaction."""
from .item_sprite_plan import iter_render_steps
from .item_sprite_render import WorldItemRenderer
from .liquid_projection import LiquidProjection
from .cell import integer_types


def projection_plan(document, profile, targets, visible, opacity):
    if targets is not None:
        volume = targets.get('volume', ())
        if (len(volume) != 3 or any(isinstance(axis, bool) or not isinstance(axis, integer_types)
                                   or axis < 1 for axis in volume)):
            raise ValueError('Item projection targets need a complete positive native volume')
        sz, sx, sy = volume
        if (sx, sy, sz) != document.size:
            raise ValueError('Item projection target volume differs from its document')
        indices = tuple(index for values in targets['common'].values() for index in values)
        if any(isinstance(index, bool) or not isinstance(index, integer_types)
               or not 0 <= index < sx*sy*sz for index in indices):
            raise ValueError('Item projection targets contain an invalid palette index')
        selected = frozenset((index // sz % sx, index // (sz*sx), index % sz)
                             for index in indices)
        def target_visible(pos):
            return pos in selected and visible(pos)
    else:
        target_visible = visible
    return iter_render_steps(document, profile, target_visible, world=True, opacity=opacity)


class ItemProjection(LiquidProjection):
    def __init__(self, bridge, document, origin, profile, dimension, hidden=(), layer=None):
        LiquidProjection.__init__(self, bridge, document, origin, profile, dimension,
                                  hidden, layer, WorldItemRenderer, projection_plan)
