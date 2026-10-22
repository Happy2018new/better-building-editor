"""Water-only native construction policy over shared model ownership."""
from .liquid_render import WorldLiquidRenderer


class ProductWorldLiquidRenderer(WorldLiquidRenderer):
    # A native create is synchronous. Limiting the count cannot bound one call.
    CREATIONS_PER_FRAME = 1
    # R18 same-session evidence: the legacy +/-2 box culls the x=63 batch;
    # +/-4 restores it while keeping the decoded payload unchanged.
    BOUNDING_BOX = ((-4.,) * 3, (4.,) * 3)
