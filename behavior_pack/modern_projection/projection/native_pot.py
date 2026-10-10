"""Refresh observed decorated-pot render directions without changing sherds."""
from __future__ import unicode_literals
from .cell import freeze, thaw
from .nbt_spatial import set_scalar
from .native_pot_data import SOURCE_VERSION, PALETTE_SHA256, TEMPLATE

SCHEMA_VERSION = 1


def native_pot_actor(material, renderer):
    if material[0] != 'minecraft:decorated_pot':
        return None
    from . import block_registry as registry
    if SOURCE_VERSION != registry.source_version() or PALETTE_SHA256 != registry.fingerprint():
        raise ValueError('Native pot rendering needs observations for this block registry')
    state = registry.states(material)
    if state is None:
        return renderer
    result = thaw(freeze(renderer if isinstance(renderer, dict) else TEMPLATE))
    set_scalar(result, 'direction', state['direction'])
    return result
