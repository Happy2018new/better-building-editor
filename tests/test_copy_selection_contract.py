"""Copy closes rich group payloads while retaining the displayed selection."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_groups import group_partner
from projection.cell import actor_data, background, foreground, make_cell
from projection.model import AIR, Document, Editor
from projection.session import Session
from projection.visible_actor import entity_nbt
from test_complete_cell_workflows_r11 import WorkflowBridge, inventory_actor


SIZES = ((32, 32, 32), (64, 128, 64))
CHEST = ('minecraft:chest', 0)
DOOR = ('minecraft:wooden_door', 0)
STONE = ('minecraft:stone', 0)
WATER = ('minecraft:water', 0)
BASE = (15, 15, 15)


def selection_state(editor):
    return set(editor.selection), editor.start, editor.end, editor.selection_revision


class CopySelectionContractTests(unittest.TestCase):
    def session(self, size):
        top = (15, 16, 15)
        actor = inventory_actor(BASE)
        sentinel = {(0, 0, 0): make_cell(('minecraft:oak_fence', 0), WATER)}
        original = dict(sentinel)
        original.update({BASE: make_cell(CHEST, DOOR, actor),
                         top: make_cell(STONE, group_partner(DOOR)[1])})
        bridge = WorkflowBridge()
        session = Session(bridge)
        session.editor = Editor(Document(size, original, 'copy selection contract', 'forest'))
        session.editor.edit_layer = 0
        session.editor.source = CHEST
        session.action(session.editor.run, 'select_material')
        bridge.settle()
        self.assertEqual({BASE}, set(session.editor.selection))
        return session, bridge, original, top

    def assert_rich_cell(self, expected, actual):
        self.assertEqual(foreground(expected), foreground(actual))
        self.assertEqual(background(expected), background(actual))
        expected_actor, actual_actor = actor_data(expected), actor_data(actual)
        self.assertEqual(entity_nbt(expected_actor) or expected_actor,
                         entity_nbt(actual_actor) or actual_actor)

    def test_public_copy_preserves_selection_and_complete_payload_across_chunk_boundary(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                before = selection_state(editor)
                revision = editor.revision
                session.action(editor.run, 'copy')
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(revision, editor.revision)
                self.assertFalse(editor.undo_stack)
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertEqual((1, 2, 1), editor.clipboard['size'])
                self.assertIn('2', editor.message)

                # The source may change after copying; the clipboard is a snapshot.
                editor.material = STONE
                editor.paint_at(BASE, respect_selection=False)
                self.assertIsNone(actor_data(editor.document.get(BASE)))
                editor.start = (2, 2, 2)
                session.action(editor.run, 'paste')
                bridge.settle()
                pasted = {(2, 2, 2), (2, 3, 2)}
                self.assertEqual(pasted, set(editor.selection))
                for source, target in ((BASE, (2, 2, 2)), (top, (2, 3, 2))):
                    expected = original[source]
                    if source == BASE:
                        nbt = copy.deepcopy(actor_data(expected))
                        for axis in ('x', 'y', 'z'):
                            nbt['__value__'][axis]['__value__'] = 2
                        expected = make_cell(CHEST, DOOR, nbt)
                    self.assert_rich_cell(expected, editor.document.get(target))
                self.assert_rich_cell(original[(0, 0, 0)], editor.document.get((0, 0, 0)))
                after = dict(editor.document.blocks.items()), set(editor.selection), editor.start, editor.end
                self.assertTrue(editor.undo())
                self.assertEqual(AIR, editor.document.get((2, 2, 2)))
                self.assertEqual(AIR, editor.document.get((2, 3, 2)))
                self.assertTrue(editor.redo())
                self.assertEqual(after, (dict(editor.document.blocks.items()), set(editor.selection),
                                         editor.start, editor.end))

    def test_copy_ignores_write_masks_and_locks_without_expanding_user_selection(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, unused_top = self.session(size)
                editor = session.editor
                editor.mask = 'air'
                editor.locked_layers.update((15, 16))
                before = selection_state(editor)
                session.action(editor.run, 'copy')
                bridge.settle()
                self.assertEqual(before, selection_state(editor))
                self.assertEqual(original, dict(editor.document.blocks.items()))
                self.assertEqual((1, 2, 1), editor.clipboard['size'])
                self.assertFalse(editor.undo_stack)

    def test_invalid_group_copy_keeps_previous_clipboard_and_selection(self):
        for size in SIZES:
            with self.subTest(size=size):
                session, bridge, original, top = self.session(size)
                editor = session.editor
                session.action(editor.run, 'copy')
                bridge.settle()
                clipboard = editor.clipboard
                editor.document.blocks[top] = STONE
                before = selection_state(editor)
                session.action(editor.run, 'copy')
                bridge.settle()
                self.assertIs(clipboard, editor.clipboard)
                self.assertEqual(before, selection_state(editor))
                self.assertFalse(editor.undo_stack)


if __name__ == '__main__':
    unittest.main()
