"""Refresh native pot directions and rebuild observed sherds from typed NBT."""
from __future__ import unicode_literals
from .cell import freeze, thaw, text_type
from . import native_pot_data as pose_source
from . import native_pot_sherd_data as sherd_source
from .nbt_spatial import field_key, root_payload, scalar, set_scalar
from .native_pot_data import SOURCE_VERSION, PALETTE_SHA256, TEMPLATE
from .native_pot_sherd_data import SHERD_FIELDS
from .visible_actor import entity_nbt

SCHEMA_VERSION = 2


def native_pot_actor(material, renderer, actor=None):
    if material[0] != 'minecraft:decorated_pot':
        return None
    from . import block_registry as registry
    if SOURCE_VERSION != registry.source_version() or PALETTE_SHA256 != registry.fingerprint():
        raise ValueError('Native pot rendering needs observations for this block registry')
    for source in (pose_source, sherd_source):
        if (source.SCHEMA_VERSION != 1 or source.SOURCE_VERSION != registry.source_version() or
                source.PALETTE_SHA256 != registry.fingerprint()):
            raise ValueError('Native pot rendering needs observations for this block registry')
    state = registry.states(material)
    if state is None:
        return renderer
    result = thaw(freeze(renderer if isinstance(renderer, dict) else TEMPLATE))
    for key, value in TEMPLATE.items():
        if field_key(result, key) is None:
            result[key] = value
    set_scalar(result, 'direction', state['direction'])
    root = root_payload(entity_nbt(actor))
    if root is not None and scalar(root, 'id') in ('DecoratedPot', b'DecoratedPot'):
        sherds = root.get(field_key(root, 'sherds'))
        if isinstance(sherds, list) and len(sherds) == len(SHERD_FIELDS):
            names = []
            for tag in sherds:
                if (not isinstance(tag, dict) or scalar(tag, '__type__') != 8 or
                        not isinstance(scalar(tag, '__value__'), (bytes, text_type))):
                    break
                names.append(scalar(tag, '__value__'))
            if len(names) == len(SHERD_FIELDS):
                for key, value in zip(SHERD_FIELDS, names):
                    set_scalar(result, key, value)
                set_scalar(result, 'decoratedPotShredNamesSize', len(names))
    return result
