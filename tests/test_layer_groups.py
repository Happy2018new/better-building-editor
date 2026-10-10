"""Grouped materials obey the chosen layer and complete-cell operations."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_groups import group_partner
from projection.cell import background, foreground, make_cell
from projection.model import AIR, Document, Editor, close_group_selection

STONE = ('minecraft:stone', 0)
PLANT = ('minecraft:tall_grass', 0)
SIZES = ((8, 5, 8), (64, 128, 64))


class LayerGroupTests(unittest.TestCase):
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


if __name__ == '__main__':
    unittest.main()
