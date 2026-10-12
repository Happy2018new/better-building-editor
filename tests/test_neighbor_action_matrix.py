"""Public action inputs stay legal and native observations bind to their source."""
import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
sys.path.insert(0, str(ROOT / 'tools'))
from projection import block_registry as registry
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
                  'native': {'rows': [{'case': plan['id'], 'family': plan['family'], 'action': 'initial',
                                       'setup_writes': writes, 'writes': [], 'cells': cells}]}}
        return report, [plan]

    def test_readback_rejects_wrong_source_writes_duplicate_positions_and_unrestored_results(self):
        source, selected = self.initial_report()
        self.assertTrue(compare_local(source, selected)['all_matched'])
        for change in ('unrestored', 'source_write', 'duplicate', 'states', 'order', 'write_failed'):
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


if __name__ == '__main__':
    unittest.main()
