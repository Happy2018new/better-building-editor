# -*- coding: utf-8 -*-
"""Behavioral checks for bounded edits, history, serialized data and algorithms."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.model import AIR, Document, Editor, demo_document
from projection.catalog import TOOLS

STONE = ('minecraft:stone', 0)
WOOD = ('minecraft:planks', 1)


class EditorTests(unittest.TestCase):
    def test_every_tool_dispatches_without_out_of_bounds_or_unknown_path(self):
        self.assertGreaterEqual(len(TOOLS), 50)
        for tool, unused_group, unused_name, unused_help in TOOLS:
            e = Editor(Document((12, 12, 12)))
            e.select_box((3, 3, 3), (6, 6, 6))
            e.material = STONE
            e.run('fill')
            e.run('copy')
            e.start, e.end = (3, 3, 3), (6, 6, 6)
            e.layer = 4
            e.run(tool)
            self.assertTrue(all(e.document.contains(p) for p in e.document.blocks), tool)

    def test_two_corners_are_inclusive_and_order_independent(self):
        e = Editor(Document((8, 8, 8)))
        e.select_box((4, 5, 6), (2, 3, 4))
        self.assertEqual(27, len(e.selection))
        self.assertIn((4, 5, 6), e.selection)
        self.assertIn((2, 3, 4), e.selection)

    def test_mask_lock_and_history_round_trip(self):
        e = Editor(Document((4, 4, 4)))
        e.material = STONE
        e.locked_layers.add(0)
        self.assertEqual(48, e.run('fill'))
        e.material = WOOD
        e.mask = 'air'
        self.assertEqual(0, e.run('fill'))
        e.mask = 'solid'
        self.assertEqual(48, e.run('fill'))
        final = e.document.to_data()
        e.undo()
        self.assertEqual(STONE, e.document.get((1, 1, 1)))
        e.redo()
        self.assertEqual(final, e.document.to_data())
        e.undo()
        e.undo()
        self.assertEqual({}, e.document.blocks)

    def test_failed_transform_is_atomic(self):
        e = Editor(Document((4, 4, 4)))
        e.run('fill')
        before = e.document.to_data()
        with self.assertRaises(ValueError):
            e.run('move_xp')
        self.assertEqual(before, e.document.to_data())
        self.assertEqual(1, len(e.undo_stack))

    def test_four_rotations_and_two_mirrors_restore_asymmetric_build(self):
        e = Editor(Document((8, 8, 8), {(2, 2, 2): STONE, (3, 4, 5): WOOD}))
        e.select_box((1, 1, 1), (6, 6, 6))
        before = e.document.to_data()
        for unused in range(4):
            e.run('rotate_y90')
        self.assertEqual(before, e.document.to_data())
        for axis in 'xyz':
            e.run('mirror_' + axis)
            e.run('mirror_' + axis)
            self.assertEqual(before, e.document.to_data())

    def test_paste_validates_full_result_before_mutating(self):
        e = Editor(Document((8, 8, 8)))
        e.select_box((0, 0, 0), (2, 2, 2))
        e.material = WOOD
        e.run('fill')
        e.run('copy')
        e.run('select_all')
        e.start = (7, 7, 7)
        before = e.document.to_data()
        with self.assertRaises(ValueError):
            e.run('paste')
        self.assertEqual(before, e.document.to_data())
        e.start = (4, 4, 4)
        self.assertEqual(27, e.run('paste_airless'))
        self.assertEqual(WOOD, e.document.get((6, 6, 6)))

    def test_flood_stops_at_material_boundary_and_selection(self):
        e = Editor(Document((5, 1, 1), {(2, 0, 0): STONE}))
        e.material = WOOD
        self.assertEqual(2, e.run('flood'))
        self.assertEqual(AIR, e.document.get((3, 0, 0)))

    def test_hollow_and_fill_single_cell_hole(self):
        e = Editor(Document((3, 3, 3)))
        e.run('fill')
        self.assertEqual(1, e.run('hollow'))
        self.assertEqual(AIR, e.document.get((1, 1, 1)))
        self.assertEqual(1, e.run('fill_holes'))
        self.assertEqual(27, len(e.document.blocks))

    def test_noise_determinism_and_different_seed(self):
        a, b = Editor(Document((8, 4, 8))), Editor(Document((8, 4, 8)))
        a.run('noise')
        b.run('noise')
        self.assertEqual(a.document.blocks, b.document.blocks)
        b.seed = 43
        b.run('noise')
        self.assertNotEqual(a.document.blocks, b.document.blocks)

    def test_config_round_trip_and_reject_bad_data(self):
        doc = demo_document()
        self.assertEqual(doc.blocks, Document.from_data(json.loads(json.dumps(doc.to_data()))).blocks)
        bad = doc.to_data()
        bad['blocks'].append([99, 0, 0, 'minecraft:stone', 0])
        with self.assertRaises(ValueError):
            Document.from_data(bad)
        with self.assertRaises(ValueError):
            Document((64, 64, 64))

    def test_palette_flattening_matches_sdk_x_y_z_order(self):
        doc = Document((3, 4, 5), {(2, 1, 3): STONE})
        self.assertEqual([48], doc.palette_data()['common'][STONE])

    def test_directional_blocks_cannot_silently_rotate_with_wrong_metadata(self):
        e = Editor(Document((3, 3, 3), {(1, 1, 1): ('minecraft:oak_stairs', 0)}))
        with self.assertRaises(ValueError):
            e.run('rotate_y90')
        self.assertEqual(0, e.revision)

    def test_new_edit_invalidates_redo_and_history_is_bounded(self):
        e = Editor(Document((1, 1, 1)))
        for unused in range(60):
            e.run('fill')
            e.run('erase')
        self.assertLessEqual(len(e.undo_stack), 50)
        e.undo()
        e.material = WOOD
        e.run('fill')
        self.assertFalse(e.redo())


if __name__ == '__main__':
    unittest.main()
