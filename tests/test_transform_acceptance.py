"""Focused acceptance data exercises public transforms and staged transactions."""
import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.block_groups import actor_pair_position, group_partner
from projection.cell import AIR, actor_data, background, foreground
from projection.debug_blueprints import material
from projection.debug_transform_acceptance import CASES, METADATA, PREFIX, build, prepare
from projection.geometry_palette import prepare_palette
from projection.jobs import EditJob
from projection.model import Document, Editor
from projection.nbt_spatial import root_payload, scalar
from projection.storage import Selection
from projection.visible_actor import entity_nbt

OPERATIONS = ('rotate_y90', 'rotate_y180', 'rotate_y270', 'mirror_x', 'mirror_y', 'mirror_z')
INVERSES = dict(zip(OPERATIONS, ('rotate_y270', 'rotate_y180', 'rotate_y90',
                                'mirror_x', 'mirror_y', 'mirror_z')))
# Independent signed coordinate matrices, rather than Editor._transform helpers.
MATRICES = {
    'rotate_y90': ((0, 0, -1), (0, 1, 0), (1, 0, 0)),
    'rotate_y180': ((-1, 0, 0), (0, 1, 0), (0, 0, -1)),
    'rotate_y270': ((0, 0, 1), (0, 1, 0), (-1, 0, 0)),
    'mirror_x': ((-1, 0, 0), (0, 1, 0), (0, 0, 1)),
    'mirror_y': ((1, 0, 0), (0, -1, 0), (0, 0, 1)),
    'mirror_z': ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
}


def target_point(point, lo, hi, operation):
    matrix = MATRICES[operation]
    def vector(value):
        return tuple(sum(matrix[axis][i] * value[i] for i in range(3)) for axis in range(3))
    corners = [vector((x, y, z)) for x in (lo[0], hi[0])
               for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
    origin = tuple(min(pos[axis] for pos in corners) for axis in range(3))
    result = vector(point)
    return tuple(result[i] - origin[i] + lo[i] for i in range(3))


def editor_for(identity, size=None):
    source = build(identity)
    editor = Editor(Document(size or source.size, source.blocks.copy(), source.name, source.biome))
    prepare(editor, identity)
    return editor


def state(editor):
    return (dict(editor.document.blocks.items()), set(editor.selection),
            editor.start, editor.end, editor.revision,
            list(editor.undo_stack), list(editor.redo_stack))


def entity(value):
    return root_payload(entity_nbt(actor_data(value)))


class TransformAcceptanceTests(unittest.TestCase):
    def test_candidates_are_independent_legal_native_documents_with_palette_preflight(self):
        for metadata in METADATA:
            identity = metadata[0]
            with self.subTest(identity=identity):
                source, reopened = build(identity), build(identity)
                self.assertEqual(source.blocks, reopened.blocks)
                self.assertIsNot(source.blocks, reopened.blocks)
                before = source.blocks.copy()
                for pos, cell in source.blocks.items():
                    self.assertTrue(source.contains(pos))
                    for layer in (foreground(cell), background(cell)):
                        self.assertEqual(layer, registry.canonical(layer))
                prepared = prepare_palette(source.palette_data())
                self.assertEqual((source.size[2], source.size[0], source.size[1]), prepared['volume'])
                self.assertEqual(before, source.blocks)
                restored = Document.from_data(json.loads(json.dumps(source.to_data())))
                self.assertEqual(source.blocks, restored.blocks)

    def test_all_six_operations_relocate_selected_cells_without_drift_and_inverse_restores(self):
        for identity in CASES:
            for operation in OPERATIONS:
                with self.subTest(identity=identity, operation=operation):
                    editor = editor_for(identity)
                    before = dict(editor.document.blocks.items())
                    selection = set(editor.selection)
                    lo, hi = CASES[identity]['selection']
                    expected = {target_point(pos, lo, hi, operation) for pos in selection}
                    editor.run(operation)
                    self.assertEqual(expected, set(editor.selection))
                    for pos, cell in before.items():
                        target = target_point(pos, lo, hi, operation) if pos in selection else pos
                        self.assertEqual(foreground(cell)[0], foreground(editor.document.get(target))[0])
                        self.assertEqual(background(cell)[0], background(editor.document.get(target))[0])
                    editor.run(INVERSES[operation])
                    self.assertEqual(before, dict(editor.document.blocks.items()))
                    self.assertEqual(selection, set(editor.selection))

    def test_t01_literal_markers_and_stair_direction_follow_non_square_quarter_turn(self):
        editor = editor_for(PREFIX + 't01')
        editor.run('rotate_y90')
        expected = (((6, 1, 2), 'red_concrete'), ((6, 1, 8), 'lime_concrete'),
                    ((2, 1, 2), 'blue_concrete'), ((2, 1, 8), 'yellow_concrete'),
                    ((6, 5, 2), 'magenta_concrete'))
        for pos, name in expected:
            self.assertEqual(material(name), foreground(editor.document.get(pos)))
        self.assertEqual(2, registry.states(foreground(editor.document.get((5, 2, 3))))['weirdo_direction'])
        self.assertEqual(((2, 1, 2), (6, 5, 8)), (editor.start, editor.end))

    def test_each_candidate_undo_redo_restores_cells_and_displayed_selection(self):
        for identity in CASES:
            with self.subTest(identity=identity):
                editor = editor_for(identity)
                before = state(editor)[:4]
                editor.run('rotate_y90')
                after = state(editor)[:4]
                self.assertEqual(1, len(editor.undo_stack))
                self.assertTrue(editor.undo())
                self.assertEqual(before, state(editor)[:4])
                self.assertTrue(editor.redo())
                self.assertEqual(after, state(editor)[:4])

    def test_t04_chest_references_and_distinct_inventories_survive_all_operations_and_reload(self):
        identity = PREFIX + 't04'
        lo, hi = CASES[identity]['selection']
        for operation in OPERATIONS:
            with self.subTest(operation=operation):
                editor = editor_for(identity)
                source = copy.deepcopy(dict(editor.document.blocks.items()))
                editor.run(operation)
                restored = Document.from_data(json.loads(json.dumps(editor.document.to_data())))
                self.assertEqual(editor.document.blocks, restored.blocks)
                for pair in CASES[identity]['pairs']:
                    for index, pos in enumerate(pair):
                        target = target_point(pos, lo, hi, operation)
                        partner = target_point(pair[1-index], lo, hi, operation)
                        value = restored.get(target)
                        self.assertEqual(partner, actor_pair_position(value, target))
                        self.assertEqual(target, tuple(scalar(entity(value), axis) for axis in 'xyz'))
                        self.assertEqual(entity(source[pos])['Items'], entity(value)['Items'])
                    roles = [scalar(entity(restored.get(target_point(pos, lo, hi, operation))), 'pairlead')
                             for pos in pair]
                    self.assertEqual({0, 1}, set(roles))

    def test_t05_four_rail_types_have_supported_slope_top_neighbor_and_closed_curve(self):
        row = CASES[PREFIX + 't05']
        document = build(PREFIX + 't05')
        for name, z, pair in zip(row['rail_names'], row['lanes'], row['slope_top_pairs']):
            self.assertEqual('minecraft:' + name, foreground(document.get(pair[0]))[0])
            self.assertEqual(2, registry.states(foreground(document.get(pair[0])))['rail_direction'])
            self.assertEqual(1, registry.states(foreground(document.get(pair[1])))['rail_direction'])
            for x, y in ((3, 2), (4, 2), (5, 3), (6, 3), (7, 3), (8, 2), (9, 2)):
                self.assertNotEqual(AIR, document.get((x, y-1, z)))
        for pos, shape in (((3, 2, 23), 6), ((9, 2, 23), 7),
                           ((3, 2, 26), 9), ((9, 2, 26), 8)):
            self.assertEqual(shape, registry.states(foreground(document.get(pos)))['rail_direction'])

    def test_t08_half_door_selection_closes_partner_before_transform(self):
        editor = editor_for(PREFIX + 't08')
        bottom, top = CASES[PREFIX + 't08']['door']
        editor.select_box(bottom, bottom)
        self.assertEqual({bottom, top}, set(editor.selection))
        before = dict(editor.document.blocks.items())
        editor.run('mirror_y')
        self.assertEqual(before, dict(editor.document.blocks.items()))
        self.assertFalse(editor.undo_stack)  # This native two-cell mirror is visually/data identical.

    def test_locked_group_partner_rejects_atomically_for_small_and_large_documents(self):
        for size in ((32, 20, 32), (64, 128, 64)):
            with self.subTest(size=size):
                editor = editor_for(PREFIX + 't08', size)
                editor.material = material('diamond_block')
                editor.paint_at((4, 1, 4), respect_selection=False)
                editor.undo()
                editor.locked_layers.add(16)
                before = state(editor)
                with self.assertRaises(ValueError):
                    editor.run('rotate_y90')
                self.assertEqual(before, state(editor))

    def test_out_of_bounds_non_square_rotation_keeps_existing_redo_and_selection(self):
        for size in ((24, 10, 24), (64, 128, 64)):
            with self.subTest(size=size):
                editor = Editor(Document(size))
                start = (size[0]-2, 1, 1)
                editor.document.blocks[start] = material('red_concrete')
                editor.select_box(start, (size[0]-1, 2, 6))
                editor.material = material('diamond_block')
                editor.paint_at((3, 1, 3), respect_selection=False)
                editor.undo()
                before = state(editor)
                with self.assertRaises(ValueError):
                    editor.run('rotate_y90')
                self.assertEqual(before, state(editor))

    def test_cancel_after_staged_progress_does_not_publish_document_selection_or_history(self):
        editor = editor_for(PREFIX + 't08')
        before = state(editor)
        job = EditJob(editor, 'rotate_y90')
        job.step(budget=5, seconds=1)
        self.assertFalse(job.done)
        self.assertNotEqual(editor.document.blocks, job.staged)
        self.assertEqual(before, state(editor))
        job.cancel()
        job.step(budget=5, seconds=1)
        self.assertTrue(job.done)
        self.assertFalse(job.error)
        self.assertEqual(before, state(editor))
        editor.run('rotate_y90')
        self.assertEqual(1, len(editor.undo_stack))

    def test_native_door_at_y127_preserves_partner_and_lock_rejection(self):
        editor = Editor(Document((64, 128, 64)))
        bottom = material('wooden_door', {'minecraft:cardinal_direction': 'east'})
        pos, top = (15, 126, 15), (15, 127, 15)
        editor.document.blocks[pos] = bottom
        editor.document.blocks[top] = group_partner(bottom)[1]
        editor.select_box(pos, pos)
        self.assertEqual({pos, top}, set(editor.selection))
        editor.run('rotate_y90')
        self.assertEqual(2, len(editor.document.blocks))
        editor.undo()
        editor.locked_layers.add(127)
        before = state(editor)
        with self.assertRaises(ValueError):
            editor.run('mirror_y')
        self.assertEqual(before, state(editor))

    def test_all_128_compact_chunks_transform_and_undo_as_one_transaction(self):
        editor = Editor(Document((64, 128, 64)))
        red, blue = material('red_concrete'), material('blue_concrete')
        for x in range(4):
            for y in range(8):
                for z in range(4):
                    editor.document.blocks.fill_chunk((x, y, z), red if x == 0 else blue)
        before = editor.document.blocks.copy()
        editor.run('rotate_y90')
        self.assertEqual(128, len(editor.document.blocks.chunks))
        self.assertEqual(red, editor.document.get((63, 127, 0)))
        self.assertEqual(blue, editor.document.get((63, 127, 63)))
        self.assertEqual(1, len(editor.undo_stack))
        self.assertEqual(64*128*64, len(editor.selection))
        self.assertTrue(editor.undo())
        self.assertEqual(before, editor.document.blocks)
        self.assertTrue(editor.redo())
        self.assertEqual(red, editor.document.get((0, 0, 0)))


if __name__ == '__main__':
    unittest.main()
