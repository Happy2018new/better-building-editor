# -*- coding: utf-8 -*-
"""Prepare layer-aware material edits and complete native grouped parts."""
from __future__ import unicode_literals
from .block_groups import group_partner, paired_cell_part, preserve_group_part
from .cell import AIR, background, edit_cell, foreground, layer, replace_layer


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


def _retained_parts(previous, updated, promote_background=False):
    """Match each remaining part once, including automatic layer promotion."""
    old = (foreground(previous), background(previous))
    new = (foreground(updated), background(updated))
    if promote_background and old[1] != AIR and new == (old[1], AIR):
        return set((1,))
    retained, available = set(), set((0, 1))
    for index in (0, 1):
        if old[index] != AIR and old[index] == new[index]:
            retained.add(index)
            available.discard(index)
    for index in (0, 1):
        if index in retained or old[index] == AIR:
            continue
        target = next((target for target in sorted(available) if new[target] == old[index]), None)
        if target is not None:
            retained.add(index)
            available.remove(target)
    return retained


def _remove_replaced_parts(get_cell, result, pos, mode):
    previous, updated = get_cell(pos) or AIR, result[pos]
    retained = _retained_parts(previous, updated, mode == 2) if mode == 2 else set(
        (mode,) if layer(previous, mode) == layer(updated, mode) else ())
    selected = (0, 1) if mode == 2 else (mode,)
    for index in selected:
        original = layer(previous, index)
        if original == AIR or index in retained:
            continue
        linked = paired_cell_part(get_cell, pos, index)
        if linked is None:
            continue
        partner, partner_index = linked
        other = result.get(partner, get_cell(partner) or AIR)
        original_other = get_cell(partner) or AIR
        if layer(other, partner_index) != layer(original_other, partner_index):
            continue
        erase_mode = 2 if mode == 2 and partner_index == 0 else partner_index
        result[partner] = edit_cell(other, AIR, erase_mode)
        result.removed.add(partner)


def material_changes(get_cell, pos, material, mode):
    """Preserve relocated groups; remove or place their actual partner layers."""
    previous = get_cell(pos) or AIR
    updated = edit_material(previous, material, mode)
    result = CellChanges({pos: updated})
    _remove_replaced_parts(get_cell, result, pos, mode)
    requested = foreground(material)
    if group_partner(requested) is None:
        return result
    selected = (0, 1) if mode == 2 else (mode,)
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
        partner_mode = mode if mode == 2 else index
        # Generated parts keep the reciprocal half, never the overwritten half.
        result[partner] = edit_cell(other, reciprocal, partner_mode)
        result.removed.discard(partner)
        _remove_replaced_parts(get_cell, result, partner, partner_mode)
        break
    return result


def reconcile_whole_group_steps(document, after, placements, write, locked_layers):
    """Remove old fixed partners left behind by a complete-cell overwrite."""
    def get_before(pos):
        return document.get(pos) if document.contains(pos) else None

    for pos in placements:
        previous, updated = document.get(pos), after.get(pos, AIR)
        retained = _retained_parts(previous, updated)
        for index in (0, 1):
            original = layer(previous, index)
            if index in retained or group_partner(original) is None:
                continue
            partner, partner_index = paired_cell_part(get_before, pos, index)
            other = after.get(partner, AIR)
            if layer(other, partner_index) != layer(document.get(partner), partner_index):
                continue
            if partner[1] in locked_layers:
                raise ValueError('多格方块对应部件图层已锁定，操作已取消')
            write(partner, replace_layer(other, AIR, partner_index))
        yield None
