"""Keep native lectern overhang in the selected target's own mesh."""
from . import block_registry

# Powered is a logical state, not a separate visual model. Preserve every
# registry material exactly; unknown future aux values keep their old route.
MATERIALS = frozenset(('minecraft:lectern', aux)
                      for aux in block_registry.aux_values('minecraft:lectern'))


def independent_body(material):
    return material in MATERIALS
