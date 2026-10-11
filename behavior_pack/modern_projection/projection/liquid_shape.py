"""Liquid neighborhood math with caller-supplied version rules and no SDK calls.

No built-in native height rule is assumed here. Production callers must supply
the separately validated profile for the installed game version.
"""
import math
from collections import OrderedDict

from .block_registry import states
from .cell import AIR, foreground, background
from .liquid_render_plan import LiquidSurface, WATER_NAMES, LAVA_NAMES
from .storage import integer_types

CORNERS = ((0, 0), (1, 0), (1, 1), (0, 1))
NEIGHBORS = ((0, 1, 0), (0, 0, -1), (0, 0, 1),
             (-1, 0, 0), (1, 0, 0), (0, -1, 0))


def _number(value, unit=False):
    return (not isinstance(value, bool) and isinstance(value, integer_types + (float,))
            and not math.isnan(value) and not math.isinf(value)
            and (0 <= value <= 1 if unit else value > 0))


class LiquidHeightRule(object):
    """Explicit depth heights/weights, including all sixteen saved depth states."""
    def __init__(self, heights, weights, empty_weight, above_height):
        heights, weights = tuple(heights), tuple(weights)
        if (len(heights) != 16 or len(weights) != 16
                or not all(_number(value, True) for value in heights)
                or not all(_number(value) for value in weights)
                or not _number(empty_weight) or not _number(above_height, True)):
            raise ValueError('Liquid rules need sixteen explicit finite heights and weights')
        self.heights, self.weights = heights, weights
        self.empty_weight, self.above_height = empty_weight, above_height

    def corner(self, samples):
        """Four (depth-or-None, excludes-empty, same-fluid-above) samples."""
        samples = tuple(samples)
        if len(samples) != 4:
            raise ValueError('A liquid corner needs its complete four-cell neighborhood')
        height, weight = 0., 0.
        for depth, blocked, above in samples:
            if above:
                return self.above_height
            if depth is not None:
                if isinstance(depth, bool) or not isinstance(depth, integer_types) or not 0 <= depth < 16:
                    raise ValueError('Liquid depth is outside the explicit rule')
                amount = self.weights[depth]
                height += self.heights[depth] * amount
                weight += amount
            elif not blocked:
                weight += self.empty_weight
        if not weight:
            raise ValueError('Liquid corner has no contributing source cell')
        return height / weight


class DocumentLiquidShapes(object):
    """Resolve shapes against one source document, retaining logical layers.

    Rules and block classifiers are explicit dependencies. ``blocked`` excludes
    non-liquid corner samples; ``occludes`` decides each directional face.
    Source queries have a bounded LRU and must be discarded after document edits.
    """
    CACHE_SIZE = 4096

    def __init__(self, document, rules, blocked, occludes, supported_names, flow_uv=None):
        self.document, self.rules = document, dict(rules)
        self.blocked, self.occludes = blocked, occludes
        self.supported_names = frozenset(supported_names)
        self.flow_uv = flow_uv
        self.cache, self.depths = OrderedDict(), {}
        if (not self.rules or not set(self.rules).issubset(('water', 'lava'))
                or not all(isinstance(rule, LiquidHeightRule) for rule in self.rules.values())
                or not self.supported_names or not self.supported_names.issubset(WATER_NAMES | LAVA_NAMES)
                or (self.supported_names & WATER_NAMES and 'water' not in self.rules)
                or (self.supported_names & LAVA_NAMES and 'lava' not in self.rules)):
            raise ValueError('Liquid provider requires explicit family rules and supported names')

    def _depth(self, value, family):
        names = WATER_NAMES if family == 'water' else LAVA_NAMES
        if value[0] not in names:
            return None
        if value[0] not in self.supported_names:
            raise ValueError('Liquid name has no validated shape profile: ' + value[0])
        if value not in self.depths:
            properties = states(value)
            depth = properties.get('liquid_depth') if properties is not None else None
            if isinstance(depth, bool) or not isinstance(depth, integer_types) or not 0 <= depth < 16:
                raise ValueError('Liquid state has no explicit depth: ' + value[0])
            self.depths[value] = depth
        return self.depths[value]

    def _sample(self, pos, family):
        key = pos, family
        if key in self.cache:
            result = self.cache.pop(key)
            self.cache[key] = result
            return result
        cell = self.document.get(pos) if self.document.contains(pos) else AIR
        depths = tuple(depth for depth in (self._depth(foreground(cell), family),
                                         self._depth(background(cell), family)) if depth is not None)
        if len(depths) > 1 and depths[0] != depths[1]:
            raise ValueError('Conflicting liquid depths at the same logical position')
        result = (depths[0] if depths else None, self.blocked(cell), cell)
        if len(self.cache) >= self.CACHE_SIZE:
            self.cache.popitem(last=False)
        self.cache[key] = result
        return result

    def _corner(self, pos, corner, family):
        x, y, z = pos
        cx, cz = corner
        samples = []
        for dx, dz in ((cx - 1, cz - 1), (cx, cz - 1), (cx, cz), (cx - 1, cz)):
            target = (x + dx, y, z + dz)
            depth, blocked, unused = self._sample(target, family)
            above = self._sample((target[0], y + 1, target[2]), family)[0] is not None
            samples.append((depth, blocked, above))
        return self.rules[family].corner(samples)

    def surface(self, document, pos, layer, value):
        if document is not self.document or document.get_layer(pos, layer) != value:
            raise ValueError('Liquid provider needs its unchanged complete source document')
        family = 'water' if value[0] in WATER_NAMES else 'lava' if value[0] in LAVA_NAMES else None
        if family is None or self._depth(value, family) is None:
            raise ValueError('A liquid shape was requested for a non-liquid cell')
        heights = tuple(self._corner(pos, corner, family) for corner in CORNERS)
        faces = 0
        for face, offset in enumerate(NEIGHBORS):
            neighbor = tuple(pos[axis] + offset[axis] for axis in range(3))
            depth, unused_blocked, cell = self._sample(neighbor, family)
            if depth is None and not self.occludes(cell, face):
                faces |= 1 << face
        texture, uv = ('still_water_grey' if family == 'water' else 'still_lava'), None
        if self.flow_uv is not None:
            texture, uv = self.flow_uv(document, pos, layer, value, heights)
        return LiquidSurface(pos, layer, heights, faces, texture, uv)
