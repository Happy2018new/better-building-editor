"""Versioned water rules for automatic editing, independent of strict snapshots."""
from .block_registry import canonical, states
from . import block_traits
from .water_interaction_data import SOURCE_DESTROYED_BLOCKS, SOURCE_STATE_CHANGES

WATER_NAMES = frozenset(('minecraft:water', 'minecraft:flowing_water'))


def is_water(value):
    return value[0] in WATER_NAMES


def is_source(value):
    if not is_water(value):
        return False
    return states(value).get('liquid_depth') == 0


def accepts_source(value):
    return value[0] not in SOURCE_DESTROYED_BLOCKS and block_traits.is_waterloggable(value)


def source_state(value):
    """Apply only observed source-water changes, preserving every other state."""
    value = canonical(value)
    return (value[0], SOURCE_STATE_CHANGES.get(value, value[1]))
