"""Select visibly accepted cauldron surfaces for their exact engine bundle."""
from . import cauldron_qualification_data as qualification
from . import cauldron_resource_data as resources
from .cauldron_native_data import SOURCE_SHA256
from .cauldron_profile import ENGINE_VERSION, candidate_profile

REQUIRED_GATES = frozenset(('editor', 'projection_full', 'projection_missing',
                            'geometry', 'colors', 'animation', 'occupancy',
                            'visibility', 'gallery', 'lifecycle', 'biome', 'default_path'))


def _fingerprint(value):
    return (isinstance(value, str) and len(value) == 64 and
            all(character in '0123456789abcdef' for character in value))


def production_profile(engine_version):
    if engine_version != ENGINE_VERSION or not qualification.PRODUCT_QUALIFIED:
        return None
    if (qualification.SCHEMA_VERSION != 1 or resources.SCHEMA_VERSION != 1 or
            resources.ENGINE_VERSION != ENGINE_VERSION or
            not _fingerprint(qualification.QUALIFICATION_SHA256) or
            qualification.QUALIFICATION_RESOURCE_CONTRACT_SHA256 != resources.RESOURCE_CONTRACT_SHA256 or
            qualification.QUALIFICATION_IMPLEMENTATION_CONTRACT_SHA256 != resources.IMPLEMENTATION_CONTRACT_SHA256 or
            qualification.QUALIFICATION_NATIVE_DATA_SHA256 != SOURCE_SHA256 or
            not isinstance(qualification.GATES, dict) or
            set(qualification.GATES) != REQUIRED_GATES or
            any(value is not True for value in qualification.GATES.values())):
        raise ValueError('Cauldron deployment needs complete visible acceptance for this exact bundle')
    profile = candidate_profile()
    profile.identity += (resources.RESOURCE_CONTRACT_SHA256,
                         resources.IMPLEMENTATION_CONTRACT_SHA256,
                         qualification.QUALIFICATION_SHA256)
    return profile
