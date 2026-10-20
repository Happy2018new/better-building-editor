"""Give native slope surfaces the complete mesh owned by their logical cell."""
from . import block_registry

# Four rail families / slope directions, an XYZ chunk corner, both model-name
# policies and missing hide/rebuild/restore passed the R23 short runtime set.
# This gate covers the clipped slope tip only; rail texture issues remain open.
CANDIDATE_ENABLED = True

# Center-cell clipping can truncate surfaces outside the owning voxel even
# when rail_direction and supports are intact. The candidate isolates that risk.
# Flat and curved rails retain their existing neighbor-context route.
RAIL_NAMES = ('minecraft:rail', 'minecraft:golden_rail',
              'minecraft:detector_rail', 'minecraft:activator_rail')
SLOPE_DIRECTIONS = frozenset((2, 3, 4, 5))
MATERIALS = frozenset((name, aux) for name in RAIL_NAMES
                      for aux in block_registry.aux_values(name)
                      if block_registry.states((name, aux)).get('rail_direction')
                      in SLOPE_DIRECTIONS)


def independent_body(material):
    """Keep each known slope, including its power bit, in one local draw."""
    return CANDIDATE_ENABLED and material in MATERIALS
