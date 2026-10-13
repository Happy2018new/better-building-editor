"""Cut publishes clipboard and complete-cell changes as one editor transaction."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.cell import AIR
import test_copy_selection_contract as copy_contract
from test_copy_selection_contract import BASE, STONE, SIZES, selection_state


class CutTransactionSelectionTests(unittest.TestCase):
    def session(self, size):
        return copy_contract.CopySelectionContractTests().session(size)

    def test_failed_cut_keeps_document_old_clipboard_selection_and_history(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                editor.select_box((0, 0, 0), (0, 0, 0))
                session.action(editor.run, 'copy')
                bridge.settle()
                previous_clipboard = editor.clipboard
                session.action(editor.run, 'select_material')
                bridge.settle()
                before = selection_state(editor), editor.revision, list(editor.undo_stack), list(editor.redo_stack)
                editor.locked_layers.add(top[1])
                session.action(editor.run, 'cut')
                bridge.settle()
                self.assertIsNone(session.edit_job)
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertIs(previous_clipboard, editor.clipboard)
                self.assertEqual(before, (selection_state(editor), editor.revision,
                                          list(editor.undo_stack), list(editor.redo_stack)))
                self.assertIn('\u9501\u5b9a', editor.message)

    def test_successful_cut_and_history_preserve_original_displayed_selection(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                before = selection_state(editor)
                session.action(editor.run, 'cut')
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(AIR, editor.document.get(BASE))
                self.assertEqual(AIR, editor.document.get(top))
                self.assertEqual(original[(0, 0, 0)], editor.document.get((0, 0, 0)))
                self.assertEqual((1, 2, 1), editor.clipboard['size'])
                self.assertEqual(1, len(editor.undo_stack))
                clipboard = editor.clipboard
                session.action(editor.undo)
                bridge.settle()
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertEqual(before, selection_state(editor))
                self.assertIs(clipboard, editor.clipboard)
                session.action(editor.redo)
                bridge.settle()
                self.assertEqual(AIR, editor.document.get(BASE))
                self.assertEqual(AIR, editor.document.get(top))
                self.assertEqual(before, selection_state(editor))
                self.assertIs(clipboard, editor.clipboard)

    def test_failed_cut_does_not_discard_existing_redo(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                editor.material = STONE
                editor.paint_at((5, 5, 5), respect_selection=False)
                editor.undo()
                self.assertTrue(editor.redo_stack)
                editor.locked_layers.add(top[1])
                before = list(editor.redo_stack)
                session.action(editor.run, 'cut')
                bridge.settle()
                self.assertEqual(before, editor.redo_stack)
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertTrue(editor.redo())
                self.assertEqual(STONE, editor.document.get((5, 5, 5)))


if __name__ == '__main__':
    unittest.main()
