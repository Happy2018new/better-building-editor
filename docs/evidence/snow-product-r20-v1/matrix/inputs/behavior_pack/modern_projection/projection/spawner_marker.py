"""Attach finite spawner badges to detached native palettes only."""
from collections import namedtuple

from . import spawner_marker_data as source
from . import spawner_marker_qualification as qualification
from .cell import integer_types
from .render_layout import MAX_LOGICAL_HEIGHT
from .spawner_presence import ENGINE_VERSION, NAMES, presence

_Profile = namedtuple('_Profile', 'identity markers')
REQUIRED_GATES = frozenset(('editor', 'projection_full', 'projection_missing',
                            'content', 'visibility', 'occupancy', 'restoration', 'default_path'))


def candidate_profile():
    if source.SCHEMA_VERSION != 1 or source.ENGINE_VERSION != ENGINE_VERSION:
        raise ValueError('Spawner markers require regeneration for their engine version')
    return _Profile((1, ENGINE_VERSION, source.SOURCE_SHA256,
                     source.RESOURCE_CONTRACT_SHA256), source.MARKERS)


def production_profile(engine_version):
    if engine_version != ENGINE_VERSION or not qualification.PRODUCT_QUALIFIED:
        return None
    if (qualification.SCHEMA_VERSION != 1 or set(qualification.GATES) != REQUIRED_GATES or
            any(value is not True for value in qualification.GATES.values()) or
            qualification.RESOURCE_CONTRACT_SHA256 != source.RESOURCE_CONTRACT_SHA256 or
            len(qualification.QUALIFICATION_SHA256) != 64):
        raise ValueError('Spawner marker deployment requires complete visible acceptance')
    return candidate_profile()


def append_markers(common, actors, logical_volume, overlay_base, profile):
    """The caller owns common; original cells and NBT never receive marker IDs."""
    if profile is None:
        return None
    markers = {}
    for material, indices in tuple(common.items()):
        if material[0] not in NAMES:
            continue
        payloads = actors.get(material[0], actors.get(material[0].encode('ascii'), {}))
        for index in indices:
            state = presence(material, payloads.get(index))
            markers.setdefault((profile.markers[state], 0), []).append(index)
    if not markers:
        return None
    if (logical_volume is None or len(logical_volume) != 3 or min(logical_volume) <= 0 or
            logical_volume[2] > MAX_LOGICAL_HEIGHT or overlay_base <= logical_volume[2]):
        raise ValueError('Spawner markers need a supported logical volume and separate overlay band')
    total = logical_volume[0] * logical_volume[1] * logical_volume[2]
    for material, indices in markers.items():
        if any(type(index) is bool or not isinstance(index, integer_types) or
               not 0 <= index < total for index in indices):
            raise ValueError('Spawner marker target lies outside the document')
        common.setdefault(material, []).extend(
            index + overlay_base * logical_volume[0] * logical_volume[1] for index in indices)
    return (logical_volume[0], logical_volume[1], overlay_base + logical_volume[2])
