"""Observed actor items and the lifecycle of native client item attachments.

Pose calibration belongs to the renderer. These helpers leave document NBT
untouched and never read entities or inventories from the server.
"""
from __future__ import unicode_literals
from .cell import freeze, thaw, integer_types, text_type
from .nbt_spatial import field_key, root_payload, scalar
from .visible_actor import entity_nbt

SCHEMA_VERSION = 1
FRAME_IDS = frozenset(('ItemFrame', b'ItemFrame', 'GlowItemFrame', b'GlowItemFrame'))
BANNER_NAMES = frozenset(('minecraft:standing_banner', 'minecraft:wall_banner'))


def _integer(value, minimum, maximum):
    return (isinstance(value, integer_types) and type(value) is not bool and
            minimum <= value <= maximum)


def _tag(root, name, kind):
    value = root.get(field_key(root, name))
    return value if isinstance(value, dict) and scalar(value, '__type__') == kind else None


def frame_item(material, actor):
    """Project the observed Item compound into the documented binding schema."""
    from .native_appearance import FRAME_NAMES
    if material[0] not in FRAME_NAMES:
        return None
    root = root_payload(entity_nbt(actor))
    if root is None or scalar(root, 'id') not in FRAME_IDS:
        return None
    item = root_payload(root.get(field_key(root, 'Item')))
    if item is None:
        return None
    name, damage, count = scalar(item, 'Name'), scalar(item, 'Damage'), scalar(item, 'Count')
    if (_tag(item, 'Name', 8) is None or not isinstance(name, (bytes, text_type)) or
            not name or _tag(item, 'Damage', 2) is None or not _integer(damage, 0, 65535) or
            _tag(item, 'Count', 1) is None or not _integer(count, 1, 255)):
        return None
    # Item tags stay typed: banner Type/Patterns and other native item render
    # fields use the same compound in the SDK's userData dictionary.
    raw = item.get(field_key(item, 'tag'))
    user_data = root_payload(raw) if raw is not None else {}
    if user_data is None:
        return None
    ench = user_data.get(field_key(user_data, 'ench'))
    enchanted = bool(scalar(user_data, 'ench') if isinstance(ench, dict) else ench)
    return {'newItemName': name, 'newAuxValue': damage,
            'isEnchanted': enchanted, 'userData': thaw(freeze(user_data))}


def banner_item(material, actor):
    """Keep typed banner render tags; Base is the observed item aux colour."""
    if material[0] not in BANNER_NAMES:
        return None
    root = root_payload(entity_nbt(actor))
    if root is None or scalar(root, 'id') not in ('Banner', b'Banner'):
        return None
    base = scalar(root, 'Base')
    if _tag(root, 'Base', 3) is None or not _integer(base, 0, 15):
        return None
    data = {}
    for name, kind in (('Type', 3), ('Patterns', 9)):
        key = field_key(root, name)
        if key is not None:
            value = root[key]
            # Native Patterns can be either a typed list or a raw compound
            # list, while Type is always an Int in the observed item payload.
            if name == 'Type' and _tag(root, name, kind) is None:
                return None
            if name == 'Patterns' and not (isinstance(value, list) or _tag(root, name, kind) is not None):
                return None
            data[key] = thaw(freeze(value))
    return {'newItemName': 'minecraft:banner', 'newAuxValue': base,
            'isEnchanted': False, 'userData': data}


def actor_item(material, actor):
    return frame_item(material, actor) or banner_item(material, actor)


class BoundItems(object):
    """Own native items on one actor; clear before destroying that actor.

    Rows are (stable key, native item dict, offset, rotation, scale). Offsets and
    ZYX Euler degrees are supplied by the renderer after native calibration.
    """
    def __init__(self, component, entity, model_family='minecraft', is_client_entity=True):
        if model_family not in ('minecraft', 'skeleton'):
            raise ValueError('Item attachments require an explicit native model family')
        if type(is_client_entity) is not bool:
            raise ValueError('Item attachments require an explicit client entity flag')
        self.component, self.entity = component, entity
        self.model_family, self.is_client_entity = model_family, is_client_entity
        self.bind_item = (component.BindItemToSkeletonModel if model_family == 'skeleton'
                          else component.BindItemToMinecraftModel)
        self.rows = {}

    def remove(self, key):
        current = self.rows.get(key)
        if current is None:
            return True
        if not self.component.SetBindBoneForBindItem(self.entity, current[0], b'', self.is_client_entity):
            return False
        del self.rows[key]
        return True

    def clear(self):
        success = True
        for key in tuple(self.rows):
            success = self.remove(key) and success
        return success

    def sync(self, rows):
        requested = dict((row[0], row[1:]) for row in rows)
        success = True
        for key in tuple(self.rows):
            if key not in requested:
                success = self.remove(key) and success
        for key, (item, offset, rotation, scale) in requested.items():
            content = freeze(item)
            current = self.rows.get(key)
            if current is not None and current[1] != content:
                if not self.remove(key):
                    success = False
                    continue
                current = None
            if current is None:
                identity = self.bind_item(
                    self.entity, item, b'root', self.is_client_entity, tuple(offset), tuple(rotation), float(scale))
                if not isinstance(identity, integer_types) or type(identity) is bool or identity < 0:
                    success = False
                    continue
                self.rows[key] = (identity, content, tuple(offset), tuple(rotation), float(scale))
                continue
            identity = current[0]
            updates = ((2, tuple(offset), self.component.SetBindItemOffset),
                       (3, tuple(rotation), self.component.SetBindItemRotation),
                       (4, float(scale), self.component.SetBindItemScale))
            changed = list(current)
            for index, value, setter in updates:
                if current[index] != value:
                    if setter(self.entity, identity, value, self.is_client_entity):
                        changed[index] = value
                    else:
                        success = False
            self.rows[key] = tuple(changed)
        return success
