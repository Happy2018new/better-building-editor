"""Lazy native templates for new actor-only directions and acceptance fixtures."""
from __future__ import unicode_literals
import base64
import json
import zlib
from . import block_registry as registry
from . import entity_defaults_data as source
from .cell import integer_types, thaw
from .nbt_spatial import rebase, root_payload, scalar, set_scalar

_templates = {}


def validate_source():
    if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
            source.PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native entity defaults need regeneration for this block registry')


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


def direction_actor(value, actor, pos):
    """Give newly created cells native directions before rotating or mirroring."""
    from .visible_actor import compose_actor, entity_nbt, is_envelope, render_actor
    if value[0] not in source.ACTOR_DIRECTION_NAMES or entity_nbt(actor) is not None:
        return actor
    data = nbt(value[0], pos)
    root = root_payload(data)
    renderer = render_actor(actor)
    render_root = root_payload(renderer)
    if scalar(root, 'id') == 'ShulkerBox' and render_root is not None:
        facing = scalar(render_root, 'facingDirection')
        if isinstance(facing, integer_types) and type(facing) is not bool and 0 <= facing <= 5:
            set_scalar(root, 'facing', facing)
    if is_envelope(actor):
        result = dict(actor)
        result['nbt'] = data
        return result
    return compose_actor(renderer, data)


def evidence():
    validate_source()
    return {'schema_version': source.SCHEMA_VERSION, 'game_version': source.SOURCE_VERSION,
            'palette_sha256': source.PALETTE_SHA256, 'source_sha256': source.SOURCE_SHA256,
            'source_hash_format': source.SOURCE_HASH_FORMAT,
            'probe_method': source.PROBE_METHOD, 'native_block_count': len(source.DEFAULTS)}
