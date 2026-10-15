"""Keep custom-owned liquid surfaces out of native block geometry."""
from .liquid_render_plan import WATER_NAMES, LAVA_NAMES


def owned_names(profile):
    if profile is None:
        return frozenset()
    return frozenset(getattr(profile, 'supported_names', ())) & (WATER_NAMES | LAVA_NAMES)


def identity(profile):
    return tuple(sorted(owned_names(profile)))


def suppress(entries, records, names):
    """Filter detached draw mappings; the document and surface targets stay intact."""
    if not names:
        return entries, records
    entries = dict((material, indices) for material, indices in entries.items()
                   if material[0] not in names)
    return entries, dict((material, record) for material, record in records.items()
                         if material in entries)
