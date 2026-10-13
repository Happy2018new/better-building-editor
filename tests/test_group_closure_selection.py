"""Group completion changes edit scope, never the displayed selection."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import actor_data, make_cell
from projection.model import AIR
import test_copy_selection_contract as copy_contract
from test_copy_selection_contract import BASE, CHEST, DOOR, STONE, SIZES, selection_state


class GroupClosureSelectionTests(unittest.TestCase):
    def session(self, size):
        return copy_contract.CopySelectionContractTests().session(size)

    def test_fill_completes_group_without_changing_selection_or_clipboard(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                session.action(editor.run, 'copy')
                bridge.settle()
                clipboard = editor.clipboard
                before = selection_state(editor)
                editor.edit_layer, editor.material = 2, STONE
                session.action(editor.run, 'fill')
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(make_cell(STONE, DOOR), editor.document.get(BASE))
                self.assertEqual(make_cell(STONE, original[top].background), editor.document.get(top))
                self.assertIs(clipboard, editor.clipboard)
                self.assertEqual(1, len(editor.undo_stack))
                session.action(editor.undo)
                bridge.settle()
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertEqual(before, selection_state(editor))
                session.action(editor.redo)
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(make_cell(STONE, DOOR), editor.document.get(BASE))
                self.assertEqual(make_cell(STONE, original[top].background), editor.document.get(top))

    def test_background_erase_keeps_foreground_nbt_and_exact_history_selection(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                before = selection_state(editor)
                editor.edit_layer = 1
                session.action(editor.run, 'erase')
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(make_cell(CHEST, AIR, actor_data(original[BASE])), editor.document.get(BASE))
                self.assertEqual(STONE, editor.document.get(top))
                self.assertEqual(1, len(editor.undo_stack))
                session.action(editor.undo)
                bridge.settle()
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertEqual(before, selection_state(editor))
                session.action(editor.redo)
                bridge.settle()
                self.assertEqual(before, selection_state(editor))

    def test_locked_partner_fill_and_erase_leave_selection_data_and_redo_intact(self):
        for size in SIZES:
            for tool, mode in (('fill', 1), ('erase', 1)):
                with self.subTest(size=size, tool=tool, mode=mode):
                    session, bridge, original, top = self.session(size)
                    editor = session.editor
                    editor.material = STONE
                    editor.paint_at((5, 5, 5), respect_selection=False)
                    editor.undo()
                    session.action(editor.run, 'copy')
                    bridge.settle()
                    clipboard, redo = editor.clipboard, list(editor.redo_stack)
                    before = selection_state(editor), editor.revision
                    editor.edit_layer = mode
                    editor.locked_layers.add(top[1])
                    session.action(editor.run, tool)
                    bridge.settle()
                    self.assertEqual(original, dict(editor.document.blocks.items()))
                    self.assertEqual(before, (selection_state(editor), editor.revision))
                    self.assertFalse(editor.undo_stack)
                    self.assertEqual(redo, editor.redo_stack)
                    self.assertIs(clipboard, editor.clipboard)

    def test_ordinary_small_fill_keeps_fast_path(self):
        session, bridge, unused_original, unused_top = self.session(SIZES[0])
        editor = session.editor
        editor.select_box((4, 4, 4), (5, 4, 4))
        editor.material = STONE
        with patch('projection.jobs.EditJob', side_effect=AssertionError('ordinary small fill became a job')):
            self.assertEqual(2, editor.run('fill'))
        self.assertEqual(STONE, editor.document.get((4, 4, 4)))
        self.assertEqual(STONE, editor.document.get((5, 4, 4)))


if __name__ == '__main__':
    unittest.main()
