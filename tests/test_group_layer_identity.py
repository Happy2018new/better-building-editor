"""Paired parts in two layers retain their individual edit ownership."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_edits import reconcile_whole_group_steps
from projection.block_groups import group_partner, paired_cell_part
from projection.cell import actor_data, background, foreground, make_cell
from projection.model import AIR, Document, Editor

STONE = ('minecraft:stone', 0)
SIZES = ((32, 32, 32), (64, 128, 64))
BOTTOM = (15, 15, 15)


def grouped_materials():
    values = [registry.canonical((name, registry.DEFAULT_AUX[name])) for name in registry.BLOCKS
              if group_partner((name, registry.DEFAULT_AUX[name])) is not None]
    values.extend(registry.from_states('minecraft:bed', {
        'direction': direction, 'head_piece_bit': False, 'occupied_bit': False})
                  for direction in range(4))
    values.extend(registry.from_states('minecraft:pitcher_crop', {
        'growth': growth, 'upper_block_bit': False}) for growth in (3, 7))
    values.append(registry.from_states('minecraft:seagrass', {'sea_grass_type': 'double_bot'}))
    return tuple(sorted(set(values)))


class GroupLayerIdentityTests(unittest.TestCase):
    def duplicate_group(self, size, material):
        editor = Editor(Document(size))
        editor.material = material
        for mode in (0, 1):
            editor.edit_layer = mode
            self.assertEqual(2, editor.paint_at(BOTTOM, respect_selection=False))
        offset, other = group_partner(material)
        partner = tuple(BOTTOM[i] + offset[i] for i in range(3))
        self.assertEqual(make_cell(material, material), editor.document.get(BOTTOM))
        self.assertEqual(make_cell(other, other), editor.document.get(partner))
        editor.select_box(BOTTOM, BOTTOM)
        return editor, partner, other

    def test_automatic_erase_promotes_one_complete_copy_and_undo_restores_both(self):
        materials = grouped_materials()
        self.assertGreaterEqual(len({value[0] for value in materials}), 30)
        for size in SIZES:
            for material in materials:
                for selected_half in (0, 1):
                    with self.subTest(size=size, material=material, selected_half=selected_half):
                        editor, partner, other = self.duplicate_group(size, material)
                        clicked = BOTTOM if selected_half == 0 else partner
                        original = editor.document.blocks.copy()
                        before_selection = set(editor.selection), editor.start, editor.end
                        editor.edit_layer = 2
                        self.assertEqual(2, editor.paint_at(clicked, erase=True, respect_selection=False))
                        self.assertEqual(material, editor.document.get(BOTTOM))
                        self.assertEqual(other, editor.document.get(partner))
                        self.assertEqual((partner, 0), paired_cell_part(editor.document.get, BOTTOM))
                        self.assertEqual(3, len(editor.undo_stack))
                        self.assertTrue(editor.undo())
                        self.assertEqual(original, editor.document.blocks)
                        self.assertEqual(before_selection, (set(editor.selection), editor.start, editor.end))
                        self.assertTrue(editor.redo())
                        self.assertEqual(material, editor.document.get(BOTTOM))
                        self.assertEqual(other, editor.document.get(partner))
                        self.assertEqual(2, editor.paint_at(clicked, erase=True, respect_selection=False))
                        self.assertEqual(AIR, editor.document.get(BOTTOM))
                        self.assertEqual(AIR, editor.document.get(partner))

    def test_batch_erase_promotes_one_copy_in_small_and_staged_edit_paths(self):
        for size in ((8, 5, 8), SIZES[1]):
            for material in (('minecraft:wooden_door', 0), ('minecraft:bed', 0)):
                with self.subTest(size=size, material=material):
                    base = (2, 1, 2)
                    offset, other = group_partner(material)
                    partner = tuple(base[i] + offset[i] for i in range(3))
                    original = {base: make_cell(material, material), partner: make_cell(other, other)}
                    editor = Editor(Document(size, original))
                    editor.select_box(base, base)
                    editor.edit_layer = 2
                    self.assertEqual(2, editor.run('erase'))
                    self.assertEqual(material, editor.document.get(base))
                    self.assertEqual(other, editor.document.get(partner))
                    self.assertEqual(1, len(editor.undo_stack))
                    self.assertTrue(editor.undo())
                    self.assertEqual(original, dict(editor.document.blocks.items()))
                    self.assertTrue(editor.redo())
                    self.assertEqual(material, editor.document.get(base))
                    self.assertEqual(other, editor.document.get(partner))

    def test_locked_partner_rejects_promoting_only_the_clicked_part(self):
        material = ('minecraft:wooden_door', 0)
        editor, partner, unused = self.duplicate_group(SIZES[0], material)
        original = copy.deepcopy(editor.document.to_data())
        editor.edit_layer = 2
        editor.locked_layers.add(partner[1])
        self.assertEqual(0, editor.paint_at(BOTTOM, erase=True, respect_selection=False))
        self.assertEqual(original, editor.document.to_data())
        self.assertEqual(2, len(editor.undo_stack))

    def test_strict_background_erase_preserves_foreground_typed_actor(self):
        material = ('minecraft:bed', 0)
        offset, other = group_partner(material)
        partner = tuple(BOTTOM[i] + offset[i] for i in range(3))
        actor = {'__type__': 10, '__value__': {
            'color': {'__type__': 1, '__value__': 11},
            'future': {'binary': b'\x00\xff', 'nested': (True, 1 << 40)}}}
        original = {BOTTOM: make_cell(material, material, actor),
                    partner: make_cell(other, other, actor)}
        editor = Editor(Document(SIZES[0], original))
        editor.edit_layer = 1
        self.assertEqual(2, editor.paint_at(BOTTOM, erase=True, respect_selection=False))
        for pos, expected in ((BOTTOM, material), (partner, other)):
            self.assertEqual(expected, foreground(editor.document.get(pos)))
            self.assertEqual(AIR, background(editor.document.get(pos)))
            self.assertEqual(actor, actor_data(editor.document.get(pos)))
        self.assertTrue(editor.undo())
        self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_whole_overwrite_cleans_each_removed_instance_once(self):
        material = ('minecraft:wooden_door', 0)
        offset, other = group_partner(material)
        partner = tuple(BOTTOM[i] + offset[i] for i in range(3))
        for retained_layer in (0, 1):
            with self.subTest(retained_layer=retained_layer):
                original = {BOTTOM: make_cell(material, material), partner: make_cell(other, other)}
                document = Document(SIZES[0], original)
                after = document.blocks.copy()
                after[BOTTOM] = (make_cell(material, STONE) if retained_layer == 0 else
                                 make_cell(STONE, material))
                writes = []
                def write(pos, value):
                    writes.append((pos, value))
                    after[pos] = value
                list(reconcile_whole_group_steps(document, after, (BOTTOM,), write, set()))
                expected = other if retained_layer == 0 else make_cell(AIR, other)
                self.assertEqual([(partner, expected)], writes)
                self.assertEqual(original, dict(document.blocks.items()))

    def test_whole_layer_relocation_keeps_the_existing_partner(self):
        material = ('minecraft:wooden_door', 0)
        offset, other = group_partner(material)
        partner = tuple(BOTTOM[i] + offset[i] for i in range(3))
        document = Document(SIZES[0], {BOTTOM: material, partner: other})
        after = document.blocks.copy()
        after[BOTTOM] = make_cell(STONE, material)
        writes = []
        list(reconcile_whole_group_steps(document, after, (BOTTOM,),
                                        lambda pos, value: writes.append((pos, value)), set()))
        self.assertEqual([], writes)
        self.assertEqual((partner, 0), paired_cell_part(after.get, BOTTOM, 1))


if __name__ == '__main__':
    unittest.main()
