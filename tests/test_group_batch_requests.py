"""Grouped edits retain requests across calculation and storage boundaries."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/modern_projection'))
from projection.block_groups import group_partner
from projection.cell import make_cell, foreground, background, actor_data
from projection.jobs import EditJob
from projection.model import AIR, Document, Editor
from projection.storage import Selection

STONE = ('minecraft:stone', 0)
GOLD = ('minecraft:gold_block', 0)
DOOR = ('minecraft:wooden_door', 0)
SMALL, LARGE = (24, 24, 24), (64, 128, 64)


class GroupBatchRequestTests(unittest.TestCase):
    def editor(self, size, mode=0, y=1):
        bottom, top = (2, y, 2), (2, y + 1, 2)
        pair = group_partner(DOOR)[1]
        cells = {bottom: DOOR, top: pair}
        if mode == 1:
            cells = {bottom: make_cell(GOLD, DOOR, {'keep': [1, 2]}),
                     top: make_cell(GOLD, pair, {'keep': [3, 4]})}
        editor = Editor(Document(size, cells))
        editor.edit_layer = mode
        editor.material, editor.secondary, editor.source = STONE, GOLD, DOOR
        editor.select_box((0, y, 0), (15, y + 1, 15))
        return editor, bottom, top

    def test_replace_across_batch_and_chunk_keeps_complete_group_and_history(self):
        for mode in (0, 1, 2):
            for y in (1, 15):
                with self.subTest(mode=mode, y=y):
                    editor, bottom, top = self.editor(LARGE, mode, y)
                    original = editor.document.blocks.copy()
                    selection = editor._selection_state()
                    self.assertEqual(2, editor.run('replace'))
                    read = background if mode == 1 else foreground
                    self.assertEqual(STONE, read(editor.document.get(bottom)))
                    self.assertEqual(STONE, read(editor.document.get(top)))
                    if mode == 1:
                        self.assertEqual(GOLD, foreground(editor.document.get(top)))
                        self.assertEqual({'keep': [3, 4]}, actor_data(editor.document.get(top)))
                    after = editor.document.blocks.copy()
                    self.assertTrue(editor.undo())
                    self.assertEqual(original, editor.document.blocks)
                    self.assertEqual(selection, editor._selection_state())
                    self.assertTrue(editor.redo())
                    self.assertEqual(after, editor.document.blocks)
                    self.assertEqual(selection, editor._selection_state())

    def test_pattern_requests_match_small_transaction_across_boundaries(self):
        for tool in ('checker', 'stripe_y', 'lattice', 'brick'):
            for mode in (0, 1, 2):
                for y in (1, 15):
                    with self.subTest(tool=tool, mode=mode, y=y):
                        small, bottom, top = self.editor(SMALL, mode, y)
                        large, unused, unused2 = self.editor(LARGE, mode, y)
                        small.run(tool)
                        large.run(tool)
                        self.assertEqual(dict(small.document.blocks.items()),
                                         dict(large.document.blocks.items()))

    def test_locked_partner_keeps_both_halves(self):
        for mode in (0, 1, 2):
            for tool in ('replace', 'checker'):
                editor, bottom, top = self.editor(LARGE, mode)
                original = {p: editor.document.get(p) for p in (bottom, top)}
                editor.locked_layers.add(top[1])
                editor.run(tool)
                self.assertEqual(original, {p: editor.document.get(p) for p in original})

    def test_cancel_between_request_and_apply_does_not_publish(self):
        editor, bottom, top = self.editor(LARGE)
        before = editor.document.blocks.copy(), editor._selection_state()
        job = EditJob(editor, 'checker')
        while job.processed < len(job.selection):
            job.step(budget=1, seconds=1)
        self.assertFalse(job.done)
        self.assertIsNotNone(job.requested_cells)
        job.cancel()
        job.step()
        self.assertTrue(job.done)
        self.assertEqual(before, (editor.document.blocks, editor._selection_state()))
        self.assertFalse(editor.undo_stack)

    def test_air_requests_and_omitted_shape_cells_remain_distinct(self):
        for tool in ('lattice', 'pyramid', 'roof'):
            small, unused, unused2 = self.editor(SMALL)
            large, unused, unused2 = self.editor(LARGE)
            small.material = large.material = AIR
            small.run(tool)
            large.run(tool)
            self.assertEqual(dict(small.document.blocks.items()), dict(large.document.blocks.items()))

    def test_requests_stay_compact_and_random_patterns_stay_seeded(self):
        editor, unused, unused2 = self.editor(LARGE)
        editor.select_box((0, 0, 0), (31, 31, 31))
        editor.secondary = editor.material
        job = EditJob(editor, 'checker')
        while job.processed < len(job.selection):
            job.step(budget=1, seconds=1)
        self.assertLess(job.requested_cells.memory_bytes(), 20000)
        self.assertEqual(32768, len(job.requested_positions))
        job.cancel()
        job.step()
        for tool in ('noise', 'gradient'):
            snapshots = []
            for budget in (1, 2048):
                editor, unused, unused2 = self.editor(LARGE)
                editor.seed = 1729
                job = EditJob(editor, tool)
                while not job.done:
                    job.step(budget=budget, seconds=1)
                self.assertFalse(job.error)
                snapshots.append(editor.document.blocks)
            self.assertEqual(*snapshots)


if __name__ == '__main__':
    unittest.main()
