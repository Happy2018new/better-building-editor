"""Lazy, independent native entity templates for public acceptance fixtures."""
from __future__ import unicode_literals
import base64
import json
import zlib
from . import block_registry as registry
from . import debug_entity_defaults_data as source
from .cell import thaw
from .nbt_spatial import rebase, root_payload, scalar

_templates = {}


def validate_source():
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native entity fixture defaults need regeneration for this block registry')


def _template(name):
    validate_source()
    packed = source.DEFAULTS.get(name)
    if packed is None:
        return None
    if name not in _templates:
        aux, tree = json.loads(zlib.decompress(base64.b64decode(packed)))
        _templates[name] = aux, tree
    return _templates[name]


def material(name):
    record = _template(name)
    return None if record is None else (name, record[0])


def nbt(name, pos):
    record = _template(name)
    if record is None:
        return None
    data = thaw(record[1])
    root = root_payload(data)
    delta = tuple(pos[index] - scalar(root, axis) for index, axis in enumerate(('x', 'y', 'z')))
    return rebase(data, delta)


def evidence():
    validate_source()
    return {'schema_version': source.SCHEMA_VERSION, 'game_version': source.SOURCE_VERSION,
            'palette_sha256': source.PALETTE_SHA256, 'source_sha256': source.SOURCE_SHA256,
            'source_hash_format': source.SOURCE_HASH_FORMAT,
            'probe_method': source.PROBE_METHOD, 'native_block_count': len(source.DEFAULTS)}
