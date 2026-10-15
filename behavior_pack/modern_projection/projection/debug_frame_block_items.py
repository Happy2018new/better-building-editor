"""Unqualified cube fixture with one ordinary item and one empty-frame control."""
from .cell import actor_data, background, foreground, freeze, make_cell, thaw
from .debug_item_blueprints import ORIENTATION_CASES, enchanted_observations, orientation_document
from .item_sprite_profile import frame_block_candidate_profile
from .nbt_spatial import field_key, root_payload, scalar, set_scalar
from .visible_actor import entity_nbt


def artificial_enchantment_payload(native_frame):
    """Copy a verified sword enchant tag onto an actual native block compound."""
    result = thaw(freeze(native_frame))
    root = root_payload(result)
    item = root_payload(root.get(field_key(root, 'Item'))) if root else None
    block = root_payload(item.get(field_key(item, 'Block'))) if item else None
    if (not root or scalar(root, 'id') not in ('ItemFrame', 'GlowItemFrame') or
            not item or not block or not scalar(item, 'Name') or
            scalar(item, 'Count') != 1 or scalar(item, 'Damage') is None):
        raise ValueError('Artificial block enchantment requires a filled native frame with Item.Block')
    observed = enchanted_observations()[0]['cell_nbt'][0]['nbt']
    source_root = root_payload(observed)
    source_item = root_payload(source_root[field_key(source_root, 'Item')])
    item[field_key(item, 'tag') or 'tag'] = thaw(freeze(source_item[field_key(source_item, 'tag')]))
    return result


def document(case_id, name, aux=0, enchanted=False):
    profile = frame_block_candidate_profile('3.10.0.420447')
    if profile.items.get((name, aux)) is None:
        raise ValueError('Frame block fixture requires an actually observed candidate item')
    case = next((row for row in ORIENTATION_CASES if row['id'] == case_id), None)
    if case is None:
        raise ValueError('Unknown native frame orientation')
    result = orientation_document(case_id)
    targets = ((3, 3, 2), (3, 3, 5)) if case['facing'] in (4, 5) else ((2, 3, 3), (5, 3, 3))
    enchanted_root = root_payload(entity_nbt(actor_data(result.get(targets[1]))))
    enchanted_item = root_payload(enchanted_root[field_key(enchanted_root, 'Item')])
    enchanted_tag = enchanted_item[field_key(enchanted_item, 'tag')]
    for index, position in enumerate(targets):
        cell = result.get(position)
        actor = actor_data(cell)
        root = root_payload(entity_nbt(actor))
        item_key = field_key(root, 'Item')
        if index:
            root.pop(item_key)
        else:
            item = root_payload(root[item_key])
            if not all((set_scalar(item, 'Name', name), set_scalar(item, 'Damage', aux),
                        set_scalar(item, 'Count', 1))):
                raise ValueError('Native frame template lacks typed ordinary item fields')
            tag_key = field_key(item, 'tag')
            if tag_key is not None:
                item.pop(tag_key)
            if enchanted:
                item['tag'] = enchanted_tag
        result.set_cell(position, make_cell(foreground(cell), background(cell), actor))
    return result
