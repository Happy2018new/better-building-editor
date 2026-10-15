"""Resolve opted-in plant render profiles at original destination coordinates."""
from .storage import integer_types
from .block_registry import canonical

# Native pixel acceptance is required before a profile becomes a default.
POSITION_PLANT_PROXIES = {}


def render_origin(value):
    if (not isinstance(value, (tuple, list)) or len(value) != 3 or
            any(isinstance(axis, bool) or not isinstance(axis, integer_types) for axis in value)):
        raise ValueError('Plant render origin requires three integer block coordinates')
    return tuple(value)


def position_sensitive(front, back):
    if not POSITION_PLANT_PROXIES:
        return False
    return ((front is not None and canonical(front) in POSITION_PLANT_PROXIES) or
            (back is not None and canonical(back) in POSITION_PLANT_PROXIES))


def plant_render(value, position):
    """A profile returns (proxy identifier, alpha top height) for one cell."""
    profile = POSITION_PLANT_PROXIES.get(value)
    return profile(position) if profile is not None else None
