"""Prepare layer-aware material edits and complete native grouped parts."""
from __future__ import unicode_literals
from .block_groups import group_partner, paired_cell_part, preserve_group_part
from .cell import AIR, background, edit_cell, foreground, layer


class CellChanges(dict):
    """Complete cells prepared for one material edit, ready for one transaction."""
    def __init__(self, values):
        dict.__init__(self, values)
        self.removed = set()


def edit_material(value, material, mode):
    original = layer(value, mode)
    if mode == 2 and group_partner(original) is None:
        original = background(value)
    material = preserve_group_part(foreground(material), original)
    return edit_cell(value, material, mode)


def material_changes(get_cell, pos, material, mode):
    """Preserve relocated groups; remove or place their actual partner layers."""
    previous = get_cell(pos) or AIR
    updated = edit_material(previous, material, mode)
    result = CellChanges({pos: updated})
    remaining = (foreground(updated), background(updated)) if mode == 2 else (layer(updated, mode),)
    selected = (0, 1) if mode == 2 else (mode,)
    for index in selected:
        original = layer(previous, index)
        if original == AIR or original in remaining:
            continue
        linked = paired_cell_part(get_cell, pos, index)
        if linked is None:
            continue
        partner, partner_index = linked
        other = result.get(partner, get_cell(partner) or AIR)
        erase_mode = 2 if mode == 2 and partner_index == 0 else partner_index
        result[partner] = edit_cell(other, AIR, erase_mode)
        result.removed.add(partner)
    requested = foreground(material)
    if group_partner(requested) is None:
        return result
    for index in selected:
        part = layer(updated, index)
        if part[0] != requested[0]:
            continue
        relationship = group_partner(part)
        if relationship is None:
            continue
        offset, reciprocal = relationship
        partner = tuple(pos[i] + offset[i] for i in range(3))
        other = result.get(partner, get_cell(partner) or AIR)
        result[partner] = edit_material(other, reciprocal, mode if mode == 2 else index)
        result.removed.discard(partner)
        break
    return result
