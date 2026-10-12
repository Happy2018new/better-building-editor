"""Replay native gates and static hanging moss without growth or tail deletion."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from generate_static_neighbor_rules import capabilities, generate
from projection import block_registry as registry
from projection.cell import actor_data, background, foreground, make_cell
from projection.jobs import EditJob
from projection.model import AIR, Document, Editor
from projection.static_neighbor_data import GATE_NAMES, HANGING_MOSS_NAMES
from projection import static_neighbor_data as static_source

NAME = 'minecraft:pale_hanging_moss'
STONE, WATER = ('minecraft:stone', 0), ('minecraft:water', 0)


def moss(tip=True):
    return registry.from_states(NAME, {'tip': tip})


def paint(editor, pos, value):
    editor.material = value
    return editor.paint_at(pos, respect_selection=False)


def states(editor, pos):
    return registry.states(foreground(editor.document.get(pos)))


def translated(pos):
    return pos[0] + 15, pos[1] + 10, pos[2] + 15


class StaticNeighborRuleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((ROOT / 'tools/data/native_static_neighbors_nemc_3.9.0.401155.json').read_text(encoding='utf8'))
        cls.manifest = json.loads((ROOT / 'tools/data/block_registry_manifest.json').read_text(encoding='utf8'))
        cls.palette = json.loads((ROOT / cls.manifest['source_file']).read_text(encoding='utf8'))

    def test_generator_requires_current_complete_native_observations(self):
        self.assertEqual(12, generate(check=True)['gates'])
        self.assertEqual((NAME,), HANGING_MOSS_NAMES)
        for mutate in (lambda data: data.update(restored=False),
                       lambda data: data.update(palette_sha256='0' * 64),
                       lambda data: data['native']['rows'].pop(),
                       lambda data: data['native']['rows'][1]['cells'][1]['states'].update(in_wall_bit=False)):
            with self.subTest(mutate=mutate):
                data = copy.deepcopy(self.report)
                mutate(data)
                with self.assertRaises(ValueError):
                    capabilities(data, self.palette, self.manifest)

    def test_stale_rules_reject_whole_transaction_before_edit_or_history_publication(self):
        gate = registry.canonical(('minecraft:fence_gate', 0))
        for material in (gate, moss()):
            for field, changed in (('SCHEMA_VERSION', 2), ('SOURCE_VERSION', 'NEMC next'),
                                   ('PALETTE_SHA256', '0' * 64)):
                with self.subTest(material=material, field=field):
                    editor = Editor(Document((32, 32, 32), {(15, 16, 15): material}))
                    before = editor.document.blocks.copy()
                    with patch.object(static_source, field, changed):
                        with self.assertRaisesRegex(ValueError, 'static neighbor'):
                            paint(editor, (15, 15, 15), STONE)
                    self.assertEqual(before, editor.document.blocks)
                    self.assertFalse(editor.undo_stack)
                    self.assertFalse(editor.redo_stack)

    def test_all_native_gate_rows_match_local_edits_across_chunk_boundary(self):
        count, names = 0, set()
        for row in self.report['native']['rows']:
            if row['metadata']['family'] != 'gate':
                continue
            with self.subTest(case=row['case'], action=row['action']):
                if row['action'] == 'initial':
                    editor = Editor(Document((32, 32, 32), {
                        translated(cell['pos']): (cell['value']['name'], cell['value']['aux'])
                        for cell in row['cells']}))
                for write in row['writes']:
                    paint(editor, translated(write['pos']), tuple(write['value']))
                expected = next(cell for cell in row['cells'] if cell['value']['name'] == row['metadata']['name'])
                self.assertEqual(expected['states'], states(editor, translated(expected['pos'])))
                names.add(expected['value']['name'])
                count += 1
        self.assertEqual(576, count)
        self.assertEqual(set(GATE_NAMES), names)

    def test_moss_extension_and_tip_removal_replay_native_states(self):
        for supplied_tip in (False, True):
            editor = Editor(Document((32, 32, 32), {(15, 17, 15): STONE}))
            for row in self.report['native']['rows']:
                if row['metadata'] != {'family': 'hanging_moss', 'supplied_tip': supplied_tip}:
                    continue
                if row['action'] in ('erase_middle', 'rejoin_middle'):
                    continue
                with self.subTest(supplied_tip=supplied_tip, action=row['action']):
                    for write in row['writes']:
                        paint(editor, translated(write['pos']), tuple(write['value']))
                    actual = {pos: states(editor, pos) for pos, value in editor.document.blocks.items()
                              if foreground(value)[0] == NAME}
                    expected = {translated(cell['pos']): cell['states'] for cell in row['cells']
                                if cell['value']['name'] == NAME}
                    self.assertEqual(expected, actual)

    def test_static_moss_middle_erase_preserves_tail_and_has_one_undo(self):
        source = {(15, y, 15): moss(y == 14) for y in range(14, 18)}
        editor = Editor(Document((32, 32, 32), source))
        editor.select_box((15, 15, 15), (15, 15, 15))
        self.assertEqual({(15, 15, 15)}, set(editor.selection))
        before = editor.document.blocks.copy()
        editor.paint_at((15, 15, 15), erase=True, respect_selection=False)
        after = editor.document.blocks.copy()
        self.assertTrue(states(editor, (15, 16, 15))['tip'])
        self.assertEqual(moss(), editor.document.get((15, 14, 15)))
        self.assertEqual(AIR, editor.document.get((15, 15, 15)))
        self.assertEqual(1, len(editor.undo_stack))
        editor.undo()
        self.assertEqual(before, editor.document.blocks)
        editor.redo()
        self.assertEqual(after, editor.document.blocks)

    def test_moss_passive_update_retains_actor_water_and_locked_cells(self):
        actor = {'keep': {'value': 7}}
        root = (15, 16, 15)
        supplied = make_cell(moss(), WATER, actor)
        editor = Editor(Document((32, 32, 32), {root: supplied}))
        paint(editor, (15, 15, 15), moss(False))
        cell = editor.document.get(root)
        self.assertFalse(states(editor, root)['tip'])
        self.assertEqual(actor, actor_data(cell))
        self.assertEqual(WATER, background(cell))
        editor.locked_layers.add(16)
        editor.paint_at((15, 15, 15), erase=True, respect_selection=False)
        self.assertEqual(cell, editor.document.get(root))

    def test_whole_snapshots_and_background_edits_keep_foreground_states(self):
        root = (15, 16, 15)
        editor = Editor(Document((32, 32, 32), {root: moss(False)}))
        paint(editor, (1, 1, 1), STONE)
        self.assertEqual(moss(False), editor.document.get(root))
        editor._commit('Imported state', {(15, 15, 15): moss(False)},
                       respect_selection=False, whole=True)
        self.assertEqual(moss(False), editor.document.get((15, 15, 15)))
        editor.edit_layer = 1
        paint(editor, (15, 14, 15), WATER)
        self.assertEqual(moss(False), foreground(editor.document.get((15, 15, 15))))
        self.assertEqual(moss(False), foreground(editor.document.get(root)))

    def test_job_parity_and_cancel_publish_no_partial_tip_update(self):
        source = Document((32, 32, 32), {(15, 16, 15): moss()})
        expected = Editor(Document(source.size, source.blocks.copy()))
        paint(expected, (15, 15, 15), moss(False))
        for cancel in (False, True):
            with self.subTest(cancel=cancel):
                editor = Editor(Document(source.size, source.blocks.copy()))
                editor.select_box((15, 15, 15), (15, 15, 15))
                editor.material = moss(False)
                job = EditJob(editor, 'fill')
                job.step(budget=2, seconds=1)
                self.assertFalse(job.done)
                if cancel:
                    job.cancel()
                while not job.done:
                    job.step(budget=1024, seconds=1)
                self.assertEqual(source.blocks if cancel else expected.document.blocks, editor.document.blocks)
                self.assertEqual(0 if cancel else 1, len(editor.undo_stack))


if __name__ == '__main__':
    unittest.main()
