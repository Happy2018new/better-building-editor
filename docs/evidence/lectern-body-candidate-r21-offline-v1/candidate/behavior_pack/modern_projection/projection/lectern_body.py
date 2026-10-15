"""Isolated, unqualified native lectern ownership candidate."""
from . import block_registry

CANDIDATE_ENABLED = False
MATERIALS = frozenset(('minecraft:lectern', aux)
                      for aux in block_registry.aux_values('minecraft:lectern'))


def independent_body(material):
    return CANDIDATE_ENABLED is True and material in MATERIALS
