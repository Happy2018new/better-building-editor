"""Static native metadata for local editing; no server queries are needed."""
from .block_traits_data import (SOLID_BLOCKS, SNOW_COVERABLE_BLOCKS,
                                SOURCE_SHA256, SOURCE_VERSION)
from . import block_traits_data as _data
from .block_registry import canonical


def is_solid(value):
    return value[0] in SOLID_BLOCKS


def is_snow_coverable(value):
    return value[0] in SNOW_COVERABLE_BLOCKS


def water_capabilities_status():
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
