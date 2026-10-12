"""Scaffold distances follow observed support paths, not a nearest-neighbor radius."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry as registry
from projection.cell import actor_data, background, foreground, make_cell
from projection.jobs import EditJob
from projection.model import AIR, Document, Editor
from projection.scaffold_neighbors import support
from projection import scaffold_support_data

STONE = ('minecraft:stone', 0)
SCAFFOLD = ('minecraft:scaffolding', 0)
WATER = ('minecraft:water', 0)


def place(editor, pos, value):
    editor.material = value
    return editor.paint_at(pos, respect_selection=False)


def distance(editor, pos):
    return registry.states(foreground(editor.document.get(pos)))['stability']


class ScaffoldNeighborTests(unittest.TestCase):
    def test_stale_support_table_never_rewrites_component_with_old_capabilities(self):
        supplied = registry.from_states(SCAFFOLD[0], {'stability': 2, 'stability_check': False})
        for field, value in (('SCHEMA_VERSION', 99), ('SOURCE_VERSION', 'NEMC future'),
                             ('PALETTE_SHA256', '0' * 64)):
            editor = Editor(Document((4, 4, 4), {(1, 2, 1): supplied}))
            before = editor.document.blocks.copy()
            with self.subTest(field=field), patch.object(scaffold_support_data, field, value):
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    support(STONE)
                with self.assertRaisesRegex(ValueError, 'regeneration'):
                    place(editor, (1, 1, 1), STONE)
                self.assertEqual(before, editor.document.blocks)
                self.assertFalse(editor.undo_stack)

    def test_unmeasured_floor_preserves_snapshot_and_its_vertical_boundary(self):
        scaffold = registry.from_states(SCAFFOLD[0], {'stability': 5, 'stability_check': True})
        editor = Editor(Document((32, 32, 32), {(15, 2, 15): scaffold}))
        place(editor, (15, 1, 15), ('minecraft:diamond_block', 0))
        self.assertEqual(scaffold, editor.document.get((15, 2, 15)))
        place(editor, (15, 3, 15), SCAFFOLD)
        self.assertEqual(5, distance(editor, (15, 3, 15)))
        self.assertIsNone(support(('minecraft:diamond_block', 0)))
        self.assertIsNone(support(('example:custom_support', 0)))
        self.assertFalse(support(AIR))

    def test_top_and_bottom_half_supports_match_native_state_observations(self):
        self.assertTrue(support(('minecraft:oak_slab', 1)))
        self.assertFalse(support(('minecraft:oak_slab', 0)))
        self.assertTrue(support(('minecraft:oak_stairs', 4)))
        self.assertFalse(support(('minecraft:oak_stairs', 0)))
        self.assertIsNone(support(('minecraft:oak_stairs', 5)))
        editor = Editor(Document((32, 32, 32)))
        place(editor, (15, 1, 15), ('minecraft:oak_slab', 0))
        place(editor, (15, 2, 15), SCAFFOLD)
        self.assertEqual(7, distance(editor, (15, 2, 15)))
        before = editor.document.blocks.copy()
        place(editor, (15, 1, 15), ('minecraft:oak_slab', 1))
        self.assertEqual(0, distance(editor, (15, 2, 15)))
        editor.undo()
        self.assertEqual(before, editor.document.blocks)

    def test_span_and_remote_new_support_recompute_across_chunk_boundary(self):
        editor = Editor(Document((64, 32, 32), {(15, 1, 15): STONE}))
        for x in range(15, 30):
            place(editor, (x, 2, 15), SCAFFOLD)
        self.assertEqual(list(range(7)) + [7] * 8,
                         [distance(editor, (x, 2, 15)) for x in range(15, 30)])
        before = editor.document.blocks.copy()
        place(editor, (29, 1, 15), STONE)
        self.assertEqual([min(x - 15, 29 - x, 7) for x in range(15, 30)],
                         [distance(editor, (x, 2, 15)) for x in range(15, 30)])
        after = editor.document.blocks.copy()
        editor.undo()
        self.assertEqual(before, editor.document.blocks)
        editor.redo()
        self.assertEqual(after, editor.document.blocks)

    def test_horizontal_distance_propagates_up_but_not_down(self):
        editor = Editor(Document((32, 32, 32), {(15, 1, 15): STONE}))
        for x in range(15, 20):
            place(editor, (x, 2, 15), SCAFFOLD)
        for y in range(3, 22):
            place(editor, (19, y, 15), SCAFFOLD)
        self.assertTrue(all(distance(editor, (19, y, 15)) == 4 for y in range(2, 22)))
        place(editor, (19, 1, 15), SCAFFOLD)
        self.assertEqual(7, distance(editor, (19, 1, 15)))
        editor.paint_at((17, 2, 15), erase=True, respect_selection=False)
        self.assertEqual(2, distance(editor, (16, 2, 15)) + 1)
        self.assertTrue(all(distance(editor, (19, y, 15)) == 7 for y in range(1, 22)))
        self.assertNotEqual(AIR, editor.document.get((19, 21, 15)))

    def test_layer_actor_and_transient_check_bit_are_preserved(self):
        actor = {'keep': {'value': 3}}
        value = registry.from_states(SCAFFOLD[0], {'stability': 6, 'stability_check': True})
        editor = Editor(Document((32, 32, 32), {(15, 2, 15): make_cell(value, WATER, actor)}))
        place(editor, (15, 1, 15), STONE)
        cell = editor.document.get((15, 2, 15))
        self.assertEqual(0, distance(editor, (15, 2, 15)))
        self.assertTrue(registry.states(foreground(cell))['stability_check'])
        self.assertEqual(WATER, background(cell))
        self.assertEqual(actor, actor_data(cell))
        editor.edit_layer = 1
        editor.paint_at((15, 1, 15), erase=True, respect_selection=False)
        self.assertEqual(cell, editor.document.get((15, 2, 15)))

    def test_locked_and_whole_snapshot_cells_are_distance_boundaries(self):
        supplied = registry.from_states(SCAFFOLD[0], {'stability': 2, 'stability_check': False})
        editor = Editor(Document((32, 32, 32), {(15, 2, 15): supplied}))
        editor.locked_layers.add(2)
        place(editor, (15, 3, 15), SCAFFOLD)
        self.assertEqual(supplied, editor.document.get((15, 2, 15)))
        self.assertEqual(2, distance(editor, (15, 3, 15)))
        editor = Editor(Document((32, 32, 32)))
        editor._commit('Snapshot', {(15, 2, 15): supplied}, respect_selection=False, whole=True)
        self.assertEqual(supplied, editor.document.get((15, 2, 15)))

    def test_job_parity_and_cancellation_publish_no_partial_component(self):
        source = {(15, 1, 15): STONE}
        source.update(((15, y, 15), SCAFFOLD) for y in range(2, 24))
        source.update(((x, 23, 15), SCAFFOLD) for x in range(16, 24))
        expected = Editor(Document((32, 32, 32), source))
        expected.paint_at((15, 1, 15), erase=True, respect_selection=False)
        for cancel in (False, True):
            editor = Editor(Document((32, 32, 32), source))
            editor.select_box((15, 1, 15), (15, 1, 15))
            job = EditJob(editor, 'erase')
            job.step(budget=4, seconds=1)
            self.assertFalse(job.done)
            if cancel:
                job.cancel()
            while not job.done:
                job.step(budget=128, seconds=1)
            self.assertEqual(Editor(Document((32, 32, 32), source)).document.blocks if cancel
                             else expected.document.blocks, editor.document.blocks)
            self.assertEqual(0 if cancel else 1, len(editor.undo_stack))

    def test_native_topology_survivors_replay_exact_support_distances(self):
        path = ROOT / 'tools/data/native_scaffold_topology_nemc_3.9.0.401155.json'
        report = json.loads(path.read_text(encoding='utf8'))
        current = None
        from verify_scaffolding_native import plans
        cases = plans()
        for row in report['native']['rows']:
            if row['case'] != current:
                current = row['case']
                shift = lambda pos: (pos[0] + 15, pos[1] + 15, pos[2] + 15)
                editor = Editor(Document((64, 64, 64), {shift(pos): value for pos, value in cases[current]['setup']}))
            for write in row['writes']:
                place(editor, shift(write['pos']), tuple(write['value']))
            for cell in row['cells']:
                if cell['value']['name'] == SCAFFOLD[0]:
                    with self.subTest(case=current, action=row['action'], pos=cell['pos']):
                        self.assertEqual(cell['states']['stability'], distance(editor, shift(cell['pos'])))


if __name__ == '__main__':
    unittest.main()
