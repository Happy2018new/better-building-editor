"""Static native metadata for local editing; no server queries are needed."""
from .block_traits_data import SOLID_BLOCKS, SOURCE_SHA256, SOURCE_VERSION


def is_solid(value):
    return value[0] in SOLID_BLOCKS
