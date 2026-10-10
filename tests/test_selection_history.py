"""Selections changed by an edit travel with that edit through history."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.jobs import EditJob
from projection.model import Document, Editor
from projection.storage import Selection

STONE = ('minecraft:stone', 0)
SIZES = ((12, 4, 12), (64, 128, 64))


def snapshot(editor):
    return dict(editor.document.blocks.items()), set(editor.selection), editor.start, editor.end


class SelectionHistoryTests(unittest.TestCase):
    def test_consecutive_moves_restore_each_block_and_selection_snapshot(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size, {(2, 1, 2): STONE}))
                editor.select_box((2, 1, 2), (3, 1, 2))
                editor.step = 1
                states = [snapshot(editor)]
                for unused in range(3):
                    editor.run('move_xp')
                    states.append(snapshot(editor))
                for expected in reversed(states[:-1]):
                    self.assertTrue(editor.undo())
                    self.assertEqual(expected, snapshot(editor))
                for expected in states[1:]:
                    self.assertTrue(editor.redo())
                    self.assertEqual(expected, snapshot(editor))

    def test_rotation_mirror_and_stack_restore_irregular_selection(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size, {(2, 1, 3): STONE}))
                editor.selection = Selection(((2, 1, 3), (3, 1, 4), (3, 1, 5)))
                editor.sync_selection_bounds()
                states = [snapshot(editor)]
                for tool in ('rotate_y90', 'mirror_x', 'stack_z'):
                    editor.run(tool)
                    states.append(snapshot(editor))
                for expected in reversed(states[:-1]):
                    self.assertTrue(editor.undo())
                    self.assertEqual(expected, snapshot(editor))
                for expected in states[1:]:
                    self.assertTrue(editor.redo())
                    self.assertEqual(expected, snapshot(editor))

    def test_empty_move_is_selection_history_without_document_dirtying(self):
        for size in SIZES:
            with self.subTest(size=size):
                editor = Editor(Document(size))
                editor.select_box((2, 1, 2), (3, 1, 2))
                before = snapshot(editor)
                editor.step = 1
                self.assertEqual(0, editor.run('move_xp'))
                after = snapshot(editor)
                self.assertNotEqual(before, after)
                self.assertEqual(0, editor.revision)
                self.assertEqual(1, len(editor.undo_stack))
                revision = editor.selection_revision
                self.assertTrue(editor.undo())
                self.assertEqual(before, snapshot(editor))
                self.assertGreater(editor.selection_revision, revision)
                self.assertEqual(0, editor.revision)
                self.assertTrue(editor.redo())
                self.assertEqual(after, snapshot(editor))

    def test_selection_history_copies_masks_and_discards_redo_after_new_edit(self):
        editor = Editor(Document((12, 4, 12)))
        editor.select_box((2, 1, 2), (2, 1, 2))
        editor.step = 1
        before = snapshot(editor)
        editor.run('move_xp')
        editor.selection.add((8, 1, 8))
        editor.undo()
        self.assertEqual(before, snapshot(editor))
        editor.run('move_zp')
        self.assertFalse(editor.redo_stack)
        editor.undo()
        self.assertEqual(before, snapshot(editor))

    def test_all_air_paste_records_changed_selection_and_exact_start(self):
        editor = Editor(Document((12, 4, 12)))
        editor.select_box((1, 1, 1), (2, 1, 1))
        editor.run('copy')
        editor.start = (5, 1, 5)
        before = snapshot(editor)
        self.assertEqual(0, editor.run('paste'))
        after = snapshot(editor)
        self.assertEqual({(5, 1, 5), (6, 1, 5)}, set(editor.selection))
        self.assertEqual(0, editor.revision)
        self.assertTrue(editor.undo())
        self.assertEqual(before, snapshot(editor))
        self.assertTrue(editor.redo())
        self.assertEqual(after, snapshot(editor))

    def test_cancelled_transform_keeps_selection_and_history_unchanged(self):
        editor = Editor(Document(SIZES[1], {(2, 1, 2): STONE}))
        editor.select_box((2, 1, 2), (3, 1, 2))
        editor.step = 1
        before = snapshot(editor)
        job = EditJob(editor, 'move_xp')
        job.step(budget=1, seconds=1)
        job.cancel()
        job.step()
        self.assertEqual(before, snapshot(editor))
        self.assertFalse(editor.undo_stack)


if __name__ == '__main__':
    unittest.main()
