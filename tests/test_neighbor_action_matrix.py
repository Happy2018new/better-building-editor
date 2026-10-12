"""Public action inputs stay legal and native observations bind to their source."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry as registry
from projection import rail_neighbor_data as rail_source
from projection.debug_action_blueprints import ACTION_MATRIX, source_document
from projection.debug_blueprints import build, entries, material
from projection.model import Editor
from verify_neighbor_actions_native import METHOD, START, STATUS, RESTORE, compare_local, plans


class NeighborActionMatrixTests(unittest.TestCase):
    def test_public_inputs_are_disjoint_legal_snapshots_and_actions_remain_undoable(self):
        document = build(ACTION_MATRIX['fixture'])
        self.assertIn(ACTION_MATRIX['fixture'], {row[0] for row in entries('connections')})
        self.assertEqual(24, len(ACTION_MATRIX['cases']))
        occupied = set()
        for row in ACTION_MATRIX['cases']:
            initial = row['supports'] + row['blocks']
            positions = {pos for pos, name, states in initial}
            self.assertFalse(positions & occupied, row['id'])
            occupied.update(positions)
            editor = Editor(source_document(row['id']))
            self.assertEqual(positions, set(editor.document.blocks), row['id'])
            for pos, name, states in initial:
                self.assertEqual(material(name, states), document.get(pos))
            for action, writes in row['actions']:
                for pos, name, states in writes:
                    self.assertTrue(document.contains(pos), (row['id'], action, pos))
                    value = material(name, states)
                    self.assertEqual(value, registry.from_states(value[0], registry.states(value)))
                    editor.material = value
                    before = editor.document.blocks.copy()
                    changed = editor.paint_at(pos, respect_selection=False)
                    after = editor.document.blocks.copy()
                    if changed:
                        editor.undo()
                        self.assertEqual(before, editor.document.blocks)
                        editor.redo()
                        self.assertEqual(after, editor.document.blocks)
        self.assertEqual({'pending'}, set(ACTION_MATRIX['acceptance'].values()))

    def initial_report(self):
        plan = plans()[0]
        plan = dict(plan, actions=[plan['actions'][0]])
        writes = [{'pos': pos, 'value': value, 'returned': True,
                   'before': {'name': 'minecraft:air', 'aux': 0}} for pos, value in plan['setup']]
        cells = [{'pos': pos, 'value': {'name': value[0], 'aux': value[1]},
                  'states': registry.states(value)} for pos, value in plan['setup']]
        report = {'method': METHOD, 'completed': True, 'restored': True,
                  'game_version': registry.source_version(), 'palette_sha256': registry.fingerprint(),
                  'start': {'runtime': '1.21.120.0'},
                  'native': {'rows': [{'case': plan['id'], 'family': plan['family'], 'action': 'initial',
                                       'setup_writes': writes, 'writes': [], 'cells': cells}]}}
        return report, [plan]

    def test_readback_rejects_wrong_source_writes_duplicate_positions_and_unrestored_results(self):
        source, selected = self.initial_report()
        self.assertTrue(compare_local(source, selected)['all_matched'])
        for change in ('unrestored', 'source_write', 'duplicate', 'states', 'order', 'write_failed', 'runtime'):
            report = copy.deepcopy(source)
            row = report['native']['rows'][0]
            if change == 'unrestored':
                report['restored'] = False
            elif change == 'source_write':
                row['setup_writes'][0]['value'] = ('minecraft:gold_block', 0)
            elif change == 'duplicate':
                row['cells'].append(row['cells'][0])
            elif change == 'states':
                row['cells'][0]['states'] = {'wrong': True}
            elif change == 'order':
                row['action'] = 'other'
            elif change == 'runtime':
                report['start']['runtime'] = '1.21.100.0'
            else:
                row['setup_writes'][0]['returned'] = False
            with self.subTest(change=change), self.assertRaises(ValueError):
                compare_local(report, selected)

    def test_native_state_difference_is_preserved_without_visual_acceptance(self):
        report, selected = self.initial_report()
        row = report['native']['rows'][0]
        rail = next(cell for cell in row['cells'] if cell['value']['name'] == 'minecraft:rail')
        value = material('rail', {'rail_direction': 1})
        rail['value'], rail['states'] = {'name': value[0], 'aux': value[1]}, registry.states(value)
        result = compare_local(report, selected)
        self.assertFalse(result['all_matched'])
        self.assertEqual(1, len(result['rows'][0]['differences']))

    def test_native_callbacks_capture_their_context_and_payloads_compile(self):
        for payload in (START % plans(), STATUS, RESTORE):
            compile(payload, '<native-action>', 'exec')
        import ast
        module = ast.parse(START % plans())
        begin = next(node for node in module.body if isinstance(node, ast.FunctionDef))
        nested = {node.name for node in begin.body if isinstance(node, ast.FunctionDef)}
        self.assertTrue({'put', 'advance', 'observe', 'observe_cells'} <= nested)

    def test_native_source_variants_rotate_actions_and_states_together(self):
        selected = plans(('rail',), ('rotate_y90', 'mirror_x'), ('rail_corner',))
        self.assertEqual(['rail_corner_rotate_y90', 'rail_corner_mirror_x'], [row['id'] for row in selected])
        rotated, mirrored = selected
        self.assertEqual([((1, 2, 0), material('rail', {'rail_direction': 1}))], rotated['actions'][1][1])
        self.assertEqual([((-1, 2, 0), material('rail'))], mirrored['actions'][2][1])
        for row in selected:
            self.assertEqual(material('rail', {'rail_direction': 1 if row is rotated else 0}), row['setup'][-1][1])

    def test_versioned_native_rail_actions_replay_without_rewriting_original_differences(self):
        records = (
            ('native_neighbor_actions_r11_nemc_3.9.0.401155.json', plans()),
            ('native_neighbor_actions_r11_axes_nemc_3.9.0.401155.json',
             plans(('rail',), ('rotate_y90', 'mirror_x'),
                   ('rail_corner', 'golden_rail_corner', 'rail_slope', 'golden_rail_slope'))))
        count = 0
        for filename, selected in records:
            source = (ROOT / 'tools/data' / filename).read_bytes()
            self.assertEqual(dict(rail_source.EVIDENCE)[filename], hashlib.sha256(source).hexdigest())
            report = json.loads(source)
            self.assertFalse(report['comparison']['all_matched'])
            before = copy.deepcopy(report)
            comparison = compare_local(report, selected)
            self.assertEqual([], [row for row in comparison['rows'] if not row['matched']])
            self.assertEqual(before, report)
            count += len(comparison['rows'])
        self.assertEqual(136, count)

    def test_stale_rail_rule_version_rejects_the_transaction_atomically(self):
        editor = Editor(source_document('rail_corner'))
        before = copy.deepcopy(editor.document.to_data())
        editor.material = material('rail')
        row = next(row for row in ACTION_MATRIX['cases'] if row['id'] == 'rail_corner')
        with patch.object(rail_source, 'SOURCE_VERSION', 'unobserved'):
            with self.assertRaises(ValueError):
                editor.paint_at(row['actions'][0][1][0][0], respect_selection=False)
        self.assertEqual(before, editor.document.to_data())
        self.assertEqual([], editor.undo_stack)


if __name__ == '__main__':
    unittest.main()
