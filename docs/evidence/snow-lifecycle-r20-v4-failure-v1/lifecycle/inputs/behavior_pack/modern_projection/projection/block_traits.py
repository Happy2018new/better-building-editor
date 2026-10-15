"""Static native metadata for local editing; no server queries are needed."""
from .block_traits_data import (SOLID_BLOCKS, SNOW_COVERABLE_BLOCKS,
                                SOURCE_SHA256, SOURCE_VERSION)
from . import block_traits_data as _data
from . import block_registry as registry
from .block_registry import canonical


try:
    _integer_types = (int, long)
except NameError:
    _integer_types = (int,)


def is_solid(value):
    _validate_source('block')
    return value[0] in SOLID_BLOCKS


def _validate_source(capability):
    if (getattr(_data, 'SCHEMA_VERSION', None) != 1 or
            getattr(_data, 'SOURCE_VERSION', None) != registry.source_version() or
            getattr(_data, 'SOURCE_SHA256', None) != registry.fingerprint()):
        raise ValueError('Native ' + capability + ' capabilities need regeneration for this block registry')


def is_snow_coverable(value):
    _validate_source('snow')
    return value[0] in SNOW_COVERABLE_BLOCKS


def snow_capability(value):
    """Return exact-state evidence within its recorded native probe fixture."""
    _validate_source('snow')
    if not isinstance(value[1], _integer_types) or type(value[1]) is bool:
        return 'unknown'
    material = registry.try_canonical(value)
    if material is None:
        return 'unknown'
    name, aux = material
    if aux in getattr(_data, 'SNOW_SUPPORTED_AUX', {}).get(name, ()):
        return 'supported'
    if aux in getattr(_data, 'SNOW_UNSUPPORTED_AUX', {}).get(name, ()):
        return 'unsupported'
    return 'unknown'


def water_capabilities_status():
    _validate_source('water')
    if (getattr(_data, 'WATERLOGGABLE_BLOCKS', None) is None or
            getattr(_data, 'WATERLOGGABLE_AUX', None) is None):
        return 'unavailable'
    return 'complete' if getattr(_data, 'WATERLOGGABLE_COMPLETE', False) else 'provisional'


def is_waterloggable(value):
    """Query measured native states; incomplete data never implies a negative."""
    name, aux = canonical(value)
    if not name.startswith('minecraft:'):
        return False
    status = water_capabilities_status()
    if status == 'unavailable':
        raise ValueError('Native water capabilities have not been measured for this game version')
    if name in _data.WATERLOGGABLE_BLOCKS or aux in _data.WATERLOGGABLE_AUX.get(name, ()):
        return True
    if (status == 'complete' or name in getattr(_data, 'WATERLOGGABLE_VERIFIED_BLOCKS', ()) or
            aux in getattr(_data, 'WATERLOGGABLE_VERIFIED_AUX', {}).get(name, ())):
        return False
    raise ValueError('Native water capability is not verified: %s [%d]' % (name, aux))
