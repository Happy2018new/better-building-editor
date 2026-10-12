"""Grouped materials obey the chosen layer and complete-cell operations."""
import sys
import random
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_groups import group_partner
from projection.block_registry import from_states
from projection.cell import actor_data, background, foreground, make_cell
from projection.model import AIR, Document, Editor, close_group_selection

STONE = ('minecraft:stone', 0)
PLANT = ('minecraft:tall_grass', 0)
SIZES = ((8, 5, 8), (64, 128, 64))


class LayerGroupTests(unittest.TestCase):
    def test_move_over_group_half_removes_old_partner_and_preserves_other_layer_and_actor(self):
        door = ('minecraft:wooden_door', 0)
        water = ('minecraft:water', 0)
        source, destination, partner = (14, 15, 15), (15, 15, 15), (15, 16, 15)
        for size in ((20, 18, 20), SIZES[1]):
            for index in (0, 1):
                with self.subTest(size=size, index=index):
                    actor = {'keep': {'values': [1, 2, 3]}}
                    destination_cell = make_cell(door, water) if index == 0 else make_cell(STONE, door)
                    partner_cell = (make_cell(group_partner(door)[1], water) if index == 0 else
                                    make_cell(STONE, group_partner(door)[1], actor))
                    original = {source: STONE, destination: destination_cell, partner: partner_cell}
                    editor = Editor(Document(size, original))
                    editor.select_box(source, source)
                    editor.step = 1
                    self.assertEqual(3, editor.run('move_xp'))
                    self.assertEqual(STONE, editor.document.get(destination))
                    self.assertEqual(make_cell(AIR, water) if index == 0 else make_cell(STONE, AIR, actor),
                                     editor.document.get(partner))
                    self.assertEqual(None if index == 0 else actor, actor_data(editor.document.get(partner)))
                    self.assertEqual({(0, 0, 0), (0, 1, 0)}, editor.last_changed_chunks)
                    after = dict(editor.document.blocks.items())
                    self.assertTrue(editor.undo())
                    self.assertEqual(original, dict(editor.document.blocks.items()))
                    self.assertTrue(editor.redo())
                    self.assertEqual(after, dict(editor.document.blocks.items()))

    def test_paste_over_group_half_removes_partner_in_its_actual_layer(self):
        door = ('minecraft:wooden_door', 0)
        source, bottom, top = (1, 1, 1), (2, 1, 2), (2, 2, 2)
        for size in SIZES:
            with self.subTest(size=size):
                original = {source: STONE, bottom: make_cell(STONE, door), top: group_partner(door)[1]}
                editor = Editor(Document(size, original))
                editor.select_box(source, source)
                editor.run('copy')
                editor.start = bottom
                self.assertEqual(2, editor.run('paste'))
                self.assertEqual(STONE, editor.document.get(bottom))
                self.assertEqual(AIR, editor.document.get(top))
                self.assertTrue(editor.undo())
                self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_whole_overwrite_with_locked_old_partner_rejects_entire_operation(self):
        door = ('minecraft:wooden_door', 0)
        source, bottom, top = (1, 1, 2), (2, 1, 2), (2, 2, 2)
        for size in SIZES:
            for tool in ('move_xp', 'paste'):
                with self.subTest(size=size, tool=tool):
                    editor = Editor(Document(size, {source: STONE, bottom: door, top: group_partner(door)[1]}))
                    editor.select_box(source, source)
                    if tool == 'paste':
                        editor.run('copy')
                        editor.start = bottom
                    editor.step = 1
                    editor.locked_layers.add(top[1])
                    before = dict(editor.document.blocks.items()), set(editor.selection), editor.start, editor.end
                    with self.assertRaises(ValueError):
                        editor.run(tool)
                    self.assertEqual(before, (dict(editor.document.blocks.items()), set(editor.selection),
                                              editor.start, editor.end))
                    self.assertFalse(editor.undo_stack)

    def test_background_group_placement_erase_and_history_preserve_foreground(self):
        for size in SIZES:
            with self.subTest(size=size):
                bottom, top = (2, 1, 2), (2, 2, 2)
                editor = Editor(Document(size, {bottom: STONE, top: STONE}))
                editor.edit_layer, editor.material = 1, PLANT
                self.assertEqual(2, editor.paint_at(bottom, respect_selection=False))
                paired = group_partner(PLANT)[1]
                self.assertEqual(PLANT, background(editor.document.get(bottom)))
                self.assertEqual(paired, background(editor.document.get(top)))
                self.assertEqual({bottom, top}, set(close_group_selection(editor.document, [bottom])))
                before = editor.document.blocks.copy()
                self.assertEqual(2, editor.paint_at(bottom, erase=True, respect_selection=False))
                self.assertEqual(STONE, editor.document.get(bottom))
                self.assertEqual(STONE, editor.document.get(top))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.redo()
                self.assertEqual(STONE, editor.document.get(bottom))

    def test_foreground_erase_does_not_erase_background_group(self):
        bottom, top = (2, 1, 2), (2, 2, 2)
        pair = group_partner(PLANT)[1]
        editor = Editor(Document(SIZES[0], {bottom: make_cell(STONE, PLANT),
                                            top: make_cell(STONE, pair)}))
        editor.edit_layer = 0
        self.assertEqual(1, editor.paint_at(bottom, erase=True, respect_selection=False))
        self.assertEqual(make_cell(AIR, PLANT), editor.document.get(bottom))
        self.assertEqual(make_cell(STONE, pair), editor.document.get(top))

    def test_background_edit_does_not_erase_foreground_door(self):
        door = ('minecraft:wooden_door', 0)
        bottom, top = (2, 1, 2), (2, 2, 2)
        pair = group_partner(door)[1]
        editor = Editor(Document(SIZES[0], {bottom: door, top: pair}))
        editor.edit_layer, editor.material = 1, ('minecraft:water', 0)
        editor.paint_at(bottom, respect_selection=False)
        self.assertEqual(door, foreground(editor.document.get(bottom)))
        self.assertEqual(pair, editor.document.get(top))
        editor.paint_at(bottom, erase=True, respect_selection=False)
        self.assertEqual(door, editor.document.get(bottom))
        self.assertEqual(pair, editor.document.get(top))

    def test_background_batch_fill_replace_and_whole_copy_move_keep_parts(self):
        bottom, top = (2, 1, 2), (2, 2, 2)
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size, {bottom: STONE, top: STONE}))
                editor.edit_layer, editor.material = 1, PLANT
                editor.select_box(bottom, top)
                self.assertEqual(2, editor.run('fill'))
                expected = editor.document.blocks.copy()
                editor.selection = {bottom}
                editor.run('copy')
                self.assertEqual(2, len(editor.clipboard['blocks']))
                editor.step = 1
                editor.run('move_xp')
                self.assertEqual(AIR, editor.document.get(bottom))
                self.assertEqual(PLANT, background(editor.document.get((3, 1, 2))))
                editor.undo()
                self.assertEqual(expected, editor.document.blocks)
                editor.source, editor.material = PLANT, ('minecraft:large_fern', 0)
                editor.selection = {bottom}
                self.assertEqual(2, editor.run('replace'))
                self.assertEqual('minecraft:large_fern', background(editor.document.get(top))[0])
                self.assertEqual(STONE, foreground(editor.document.get(top)))

    def test_whole_cell_group_selection_closes_links_transitively_in_both_layers(self):
        door = ('minecraft:wooden_door', 0)
        bed = ('minecraft:bed', 0)
        bottom, top, back, back_top = (2, 1, 2), (2, 2, 2), (2, 1, 3), (2, 2, 3)
        door_top, bed_head = group_partner(door)[1], group_partner(bed)[1]
        document = Document(SIZES[0], {bottom: make_cell(door, bed),
                                       top: make_cell(door_top, bed),
                                       back: make_cell(door, bed_head),
                                       back_top: make_cell(door_top, bed_head)})
        self.assertEqual({bottom, top}, set(close_group_selection(document, [bottom], index=0)))
        self.assertEqual({bottom, back}, set(close_group_selection(document, [bottom], index=1)))
        self.assertEqual({bottom, top, back, back_top}, set(close_group_selection(document, [bottom])))

    def test_matching_groups_in_both_layers_are_edited_independently(self):
        bottom, top = (2, 1, 2), (2, 2, 2)
        paired = group_partner(PLANT)[1]
        original = {bottom: make_cell(PLANT, PLANT), top: make_cell(paired, paired)}
        for mode in (0, 1):
            with self.subTest(mode=mode):
                editor = Editor(Document(SIZES[0], original))
                editor.edit_layer = mode
                self.assertEqual(2, editor.paint_at(bottom, erase=True, respect_selection=False))
                if mode == 0:
                    self.assertEqual(make_cell(AIR, PLANT), editor.document.get(bottom))
                    self.assertEqual(make_cell(AIR, paired), editor.document.get(top))
                else:
                    self.assertEqual(PLANT, editor.document.get(bottom))
                    self.assertEqual(paired, editor.document.get(top))

    def test_young_pitcher_crops_are_single_cells_and_mature_crops_are_grouped(self):
        pos, above = (2, 1, 2), (2, 2, 2)
        for growth in range(8):
            with self.subTest(growth=growth):
                material = from_states('minecraft:pitcher_crop',
                                       {'growth': growth, 'upper_block_bit': False})
                for size in SIZES:
                    editor = Editor(Document(size))
                    editor.material = material
                    expected = 1 if growth < 3 else 2
                    self.assertEqual(expected, editor.paint_at(pos, respect_selection=False))
                    self.assertEqual(material, editor.document.get(pos))
                    if growth < 3:
                        self.assertIsNone(group_partner(material))
                        self.assertEqual(AIR, editor.document.get(above))
                    else:
                        self.assertEqual(group_partner(material)[1], editor.document.get(above))
                    editor.select_box(pos, pos)
                    self.assertEqual(expected, len(editor.selection))
                    editor.run('copy')
                    self.assertEqual(expected, len(editor.clipboard['blocks']))
                    before = editor.document.blocks.copy()
                    self.assertEqual(expected, editor.run('erase'))
                    self.assertEqual(AIR, editor.document.get(pos))
                    self.assertEqual(AIR, editor.document.get(above))
                    editor.undo()
                    self.assertEqual(before, editor.document.blocks)

    def test_imported_pitcher_seedling_does_not_require_a_missing_upper_part(self):
        seedling = from_states('minecraft:pitcher_crop', {'growth': 0, 'upper_block_bit': False})
        editor = Editor(Document(SIZES[0], {(2, 1, 2): seedling}))
        editor.select_box((2, 1, 2), (2, 1, 2))
        editor.run('copy')
        self.assertEqual(1, len(editor.clipboard['blocks']))
        self.assertEqual(1, editor.run('erase'))

    def test_new_group_cleans_up_a_different_group_covered_by_its_other_part(self):
        door, bed = ('minecraft:wooden_door', 0), ('minecraft:bed', 0)
        bottom, top, old_head = (2, 1, 2), (2, 2, 2), (2, 2, 3)
        bed_head, door_top = group_partner(bed)[1], group_partner(door)[1]
        for size in SIZES:
            for mode in (0, 1):
                with self.subTest(size=size, mode=mode):
                    original = {top: bed, old_head: bed_head}
                    if mode == 1:
                        original = {pos: make_cell(STONE, value) for pos, value in original.items()}
                    editor = Editor(Document(size, original))
                    editor.edit_layer, editor.material = mode, door
                    self.assertEqual(3, editor.paint_at(bottom, respect_selection=False))
                    self.assertEqual(door, foreground(editor.document.get(bottom)) if mode == 0 else
                                     background(editor.document.get(bottom)))
                    self.assertEqual(door_top, foreground(editor.document.get(top)) if mode == 0 else
                                     background(editor.document.get(top)))
                    self.assertEqual(AIR if mode == 0 else STONE, editor.document.get(old_head))
                    editor.undo()
                    self.assertEqual(original, dict(editor.document.blocks.items()))
                    editor.locked_layers.add(old_head[1])
                    self.assertEqual(0, editor.paint_at(bottom, respect_selection=False))
                    self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_group_generated_parts_keep_the_requested_half_when_covering_an_existing_group(self):
        door = ('minecraft:wooden_door', 0)
        bottom, top, old_top = (2, 1, 2), (2, 2, 2), (2, 3, 2)
        door_top = group_partner(door)[1]
        editor = Editor(Document(SIZES[0], {top: door, old_top: door_top}))
        editor.material = door
        self.assertEqual(3, editor.paint_at(bottom, respect_selection=False))
        self.assertEqual(door, editor.document.get(bottom))
        self.assertEqual(door_top, editor.document.get(top))
        self.assertEqual(AIR, editor.document.get(old_top))

    def test_grouped_fill_does_not_reinsert_a_removed_half_without_its_new_partner(self):
        door, bed = ('minecraft:wooden_door', 0), ('minecraft:bed', 0)
        bottom, top, old_head = (2, 1, 2), (2, 2, 2), (2, 2, 3)
        for size in SIZES:
            for mode in (0, 1):
                with self.subTest(size=size, mode=mode):
                    original = {top: bed, old_head: group_partner(bed)[1]}
                    if mode == 1:
                        original = {pos: make_cell(STONE, value) for pos, value in original.items()}
                    editor = Editor(Document(size, original))
                    editor.edit_layer, editor.material = mode, door
                    editor.selection = {bottom, top, old_head}
                    self.assertEqual(3, editor.run('fill'))
                    self.assertEqual(door, foreground(editor.document.get(bottom)) if mode == 0 else
                                     background(editor.document.get(bottom)))
                    self.assertEqual(group_partner(door)[1], foreground(editor.document.get(top)) if mode == 0 else
                                     background(editor.document.get(top)))
                    self.assertEqual(AIR if mode == 0 else STONE, editor.document.get(old_head))
                    editor.undo()
                    self.assertEqual(original, dict(editor.document.blocks.items()))

    def test_overlapping_group_placements_never_leave_unpaired_parts(self):
        materials = [('minecraft:wooden_door', 0), PLANT, ('minecraft:large_fern', 0),
                     ('minecraft:bed', 0), ('minecraft:bed', 1), ('minecraft:bed', 2),
                     ('minecraft:bed', 3), STONE, AIR]
        for size, mode in ((size, mode) for size in SIZES for mode in (0, 1)):
            editor, randomizer = Editor(Document(size)), random.Random(932)
            editor.edit_layer = mode
            for unused in range(120):
                pos = (randomizer.randrange(1, 7), randomizer.randrange(1, 4),
                       randomizer.randrange(1, 7))
                editor.material = randomizer.choice(materials)
                if unused % 3:
                    editor.paint_at(pos, respect_selection=False)
                else:
                    editor.select_box(pos, tuple(min(pos[i] + 1, editor.document.size[i] - 1)
                                                 for i in range(3)))
                    editor.run('fill')
                for target, cell in editor.document.blocks.items():
                    value = foreground(cell) if mode == 0 else background(cell)
                    relationship = group_partner(value)
                    if relationship is None:
                        continue
                    offset, expected = relationship
                    paired_pos = tuple(target[i] + offset[i] for i in range(3))
                    other = editor.document.get(paired_pos)
                    self.assertEqual(expected, foreground(other) if mode == 0 else background(other),
                                     (size, mode, unused, pos, editor.material, target, value, paired_pos))

    def test_batch_group_cleanup_preserves_parts_already_placed_by_the_same_transaction(self):
        bottom, top = (2, 1, 3), (2, 2, 3)
        door, bed = ('minecraft:wooden_door', 0), ('minecraft:bed', 0)
        for size in SIZES:
            for mode in (0, 1):
                original = {bottom: door, top: group_partner(door)[1]}
                if mode == 1:
                    original = {pos: make_cell(STONE, value) for pos, value in original.items()}
                editor = Editor(Document(size, original))
                editor.edit_layer, editor.material = mode, bed
                editor.select_box((2, 1, 2), (2, 2, 3))
                self.assertEqual(4, editor.run('fill'))
                for y in (1, 2):
                    foot, head = editor.document.get((2, y, 2)), editor.document.get((2, y, 3))
                    self.assertEqual(bed, foreground(foot) if mode == 0 else background(foot))
                    self.assertEqual(group_partner(bed)[1], foreground(head) if mode == 0 else background(head))
                editor.undo()
                self.assertEqual(original, dict(editor.document.blocks.items()))


if __name__ == '__main__':
    unittest.main()
