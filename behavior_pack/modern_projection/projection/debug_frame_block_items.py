"""Unqualified cube fixture with one ordinary item and one empty-frame control."""
from .cell import actor_data, background, foreground, make_cell
from .debug_item_blueprints import ORIENTATION_CASES, orientation_document
from .item_sprite_profile import frame_block_candidate_profile
from .nbt_spatial import field_key, root_payload, set_scalar
from .visible_actor import entity_nbt


def document(case_id, name, aux=0):
    profile = frame_block_candidate_profile('3.10.0.420447')
    if profile.items.get((name, aux)) is None:
        raise ValueError('Frame block fixture requires an actually observed candidate item')
    case = next((row for row in ORIENTATION_CASES if row['id'] == case_id), None)
    if case is None:
        raise ValueError('Unknown native frame orientation')
    result = orientation_document(case_id)
    targets = ((3, 3, 2), (3, 3, 5)) if case['facing'] in (4, 5) else ((2, 3, 3), (5, 3, 3))
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
        result.set_cell(position, make_cell(foreground(cell), background(cell), actor))
    return result
