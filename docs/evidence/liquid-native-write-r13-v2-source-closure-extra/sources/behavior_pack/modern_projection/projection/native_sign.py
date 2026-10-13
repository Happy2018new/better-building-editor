"""Observed two-sided sign NBT and state fields for native palette rendering."""
from __future__ import unicode_literals
from .cell import freeze, thaw, integer_types, text_type
from .nbt_spatial import field_key, root_payload, scalar, set_scalar
from .native_sign_data import SOURCE_VERSION, PALETTE_SHA256, TEMPLATES, STYLE_FIELDS
from . import native_sign_data as _data
from .visible_actor import entity_nbt

SCHEMA_VERSION = 1


def _field(side, name, kind):
    tag = side.get(field_key(side, name))
    if not isinstance(tag, dict) or scalar(tag, '__type__') != kind:
        return False, None
    value = scalar(tag, '__value__')
    if kind == 8:
        return isinstance(value, (bytes, text_type)), value
    if not isinstance(value, integer_types) or type(value) is bool:
        return False, None
    if kind == 1:
        return value in (0, 1), bool(value)
    return -2147483648 <= value <= 2147483647, value


def native_sign_actor(material, actor, renderer):
    """Return a sign render copy; saved text, unknown tags and actors stay intact."""
    template = TEMPLATES.get(material[0])
    if template is None:
        return None
    from . import block_registry as registry
    if (_data.SCHEMA_VERSION != 1 or SOURCE_VERSION != registry.source_version() or
            PALETTE_SHA256 != registry.fingerprint()):
        raise ValueError('Native sign rendering needs observations for this block registry')
    state = registry.states(material)
    if state is None:
        return renderer
    result = thaw(freeze(renderer)) if isinstance(renderer, dict) else {}
    for key, value in template.items():
        if field_key(result, key) is None:
            result[key] = value
    if 'ground_sign_direction' in state:
        set_scalar(result, 'signStandingRotation', state['ground_sign_direction'])
    if 'facing_direction' in state:
        set_scalar(result, 'facingDirection', state['facing_direction'])
    if 'hanging' in state:
        set_scalar(result, 'signHangingSignBit', not state['hanging'])
        set_scalar(result, 'signAttachedSignBit', state['hanging'] and state['attached_bit'])
    root = root_payload(entity_nbt(actor))
    expected = ('HangingSign', b'HangingSign') if template['signHanging'] else ('Sign', b'Sign')
    if root is None or scalar(root, 'id') not in expected:
        return result
    for name, suffix in (('FrontText', ''), ('BackText', 'Back')):
        side = root_payload(root.get(field_key(root, name)))
        if side is None:
            continue
        for source, target, kind in STYLE_FIELDS:
            valid, value = _field(side, source, kind)
            if valid:
                set_scalar(result, target + suffix, value)
    return result
