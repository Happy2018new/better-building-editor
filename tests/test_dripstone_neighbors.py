"""Local pointed-dripstone edits follow preserved NEMC state observations."""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import actor_data, background, foreground, make_cell
from projection.jobs import EditJob
from projection.model import AIR, Document, Editor
from projection.debug_blueprints import VISUAL_CASES, build

NAME = 'minecraft:pointed_dripstone'
STONE = ('minecraft:stone', 0)
WATER = ('minecraft:water', 0)


def dripstone(hanging=False, thickness='tip'):
    return registry.from_states(NAME, {'hanging': hanging, 'dripstone_thickness': thickness})


def paint(editor, pos, value):
    editor.material = value
    return editor.paint_at(pos, respect_selection=False)


def properties(editor, pos):
    return registry.states(foreground(editor.document.get(pos)))


class DripstoneNeighborTests(unittest.TestCase):
    def test_public_fixture_preserves_measured_chain_shapes_and_merged_pair(self):
        case = VISUAL_CASES['dripstone_neighbors']
        doc = build(case['fixture'])
        for row in case['chains']:
            length = row['length']
            expected = (['tip'] if length == 1 else ['frustum', 'tip'] if length == 2 else
                        ['base'] + ['middle'] * (length - 3) + ['frustum', 'tip'])
            for hanging, key in ((False, 'standing'), (True, 'hanging')):
                values = [registry.states(foreground(doc.get(pos))) for pos in row[key]]
                self.assertEqual(expected, [value['dripstone_thickness'] for value in values])
                self.assertEqual([hanging] * length, [value['hanging'] for value in values])
        for hanging, pos in enumerate(case['merged_tips']):
            self.assertEqual({'hanging': bool(hanging), 'dripstone_thickness': 'merge'},
                             registry.states(foreground(doc.get(pos))))
        first, second = case['vertical_chunk_cells']
        self.assertNotEqual(tuple(v >> 4 for v in first), tuple(v >> 4 for v in second))

    def test_edits_match_every_preserved_native_state_row(self):
        report = json.loads((ROOT / 'tools/data/native_dripstone_states_r4.json').read_text(encoding='utf8'))
        self.assertTrue(report['completed'] and report['restored'])
        self.assertEqual(28, report['native']['cases'])
        for row in report['native']['rows']:
            kind, hanging, height = row['action']
            with self.subTest(action=row['action']):
                if kind in ('reset', 'opposed'):
                    editor = Editor(Document((32, 32, 32)))
                    for y in (-1, 2 if kind == 'opposed' else 8):
                        paint(editor, (15, 12 + y, 15), STONE)
                    if kind == 'opposed':
                        for y in ((0, 1) if not height else (1, 0)):
                            paint(editor, (15, 12 + y, 15), dripstone(bool(y)))
                elif kind == 'merge':
                    editor._commit('Native merge snapshot', {
                        (15, 12 + y, 15): dripstone(bool(y), 'merge') for y in (0, 1)},
                        respect_selection=False, whole=True)
                else:
                    y = height if kind == 'erase_pair' else 7 - height if hanging else height
                    pos = (15, 12 + y, 15)
                    if kind == 'extend':
                        paint(editor, pos, dripstone(hanging))
                    else:
                        editor.paint_at(pos, erase=True, respect_selection=False)
                actual = [{'y': y, 'states': properties(editor, (15, 12 + y, 15))}
                          for y in range(8) if foreground(editor.document.get((15, 12 + y, 15)))[0] == NAME]
                self.assertEqual(row['cells'], actual)

    def test_cross_chunk_thickness_updates_share_one_undo_entry(self):
        for hanging in (False, True):
            with self.subTest(hanging=hanging):
                editor = Editor(Document((32, 32, 32)))
                step, base = (-1, 17) if hanging else (1, 14)
                positions = [(15, base + index * step, 15) for index in range(5)]
                for pos in positions[:2]:
                    paint(editor, pos, dripstone(hanging))
                before = editor.document.blocks.copy()
                paint(editor, positions[2], dripstone(hanging))
                grown = editor.document.blocks.copy()
                self.assertEqual('base', properties(editor, positions[0])['dripstone_thickness'])
                self.assertEqual('frustum', properties(editor, positions[1])['dripstone_thickness'])
                self.assertEqual('tip', properties(editor, positions[2])['dripstone_thickness'])
                self.assertEqual(3, len(editor.undo_stack))
                editor.undo()
                self.assertEqual(before, editor.document.blocks)
                editor.redo()
                self.assertEqual(grown, editor.document.blocks)
                editor.paint_at(positions[2], erase=True, respect_selection=False)
                self.assertEqual(before, editor.document.blocks)

    def test_passive_update_keeps_water_actor_and_locked_layer(self):
        actor = {'custom': {'keep': 7}}
        root = (15, 14, 15)
        editor = Editor(Document((32, 32, 32), {
            root: make_cell(dripstone(False, 'frustum'), WATER, actor),
            (15, 15, 15): dripstone()}))
        editor.locked_layers.add(15)
        locked = editor.document.get((15, 15, 15))
        paint(editor, (15, 16, 15), dripstone())
        self.assertEqual('base', properties(editor, root)['dripstone_thickness'])
        self.assertEqual(WATER, background(editor.document.get(root)))
        self.assertEqual(actor, actor_data(editor.document.get(root)))
        self.assertEqual(locked, editor.document.get((15, 15, 15)))

    def test_background_job_matches_sync_edit_and_cancel_does_not_publish(self):
        source = Document((32, 32, 32), {(15, 14, 15): dripstone(False, 'frustum'),
                                        (15, 15, 15): dripstone()})
        expected = Editor(Document(source.size, source.blocks.copy()))
        paint(expected, (15, 16, 15), dripstone())
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                editor = Editor(Document(source.size, source.blocks.copy()))
                editor.select_box((15, 16, 15), (15, 16, 15))
                editor.material = dripstone()
                job = EditJob(editor, 'fill')
                job.step(budget=2, seconds=1)
                self.assertFalse(job.done)
                if cancel:
                    job.cancel()
                while not job.done:
                    job.step(budget=1024, seconds=1)
                self.assertEqual(source.blocks if cancel else expected.document.blocks, editor.document.blocks)
                self.assertEqual(0 if cancel else 1, len(editor.undo_stack))

    def test_unrelated_edit_and_whole_cell_import_keep_explicit_snapshots(self):
        supplied = dripstone(False, 'merge')
        editor = Editor(Document((32, 32, 32), {(15, 14, 15): supplied}))
        paint(editor, (2, 2, 2), STONE)
        self.assertEqual(supplied, editor.document.get((15, 14, 15)))
        editor._commit('Imported state', {(15, 15, 15): dripstone(True, 'merge')},
                       respect_selection=False, whole=True)
        self.assertEqual(supplied, editor.document.get((15, 14, 15)))
        editor.paint_at((15, 15, 15), erase=True, respect_selection=False)
        self.assertEqual(dripstone(), editor.document.get((15, 14, 15)))
        self.assertEqual(AIR, editor.document.get((15, 15, 15)))


if __name__ == '__main__':
    unittest.main()
