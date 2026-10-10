"""Public static adjacency cases remain distinct, supported, and reproducible."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection import block_registry as registry
from projection.cell import AIR, foreground
from projection.debug_blueprints import VISUAL_CASES, build


class StaticConnectionBlueprintTests(unittest.TestCase):
    def test_gate_materials_open_states_and_both_axes_have_fixed_native_cases(self):
        metadata = VISUAL_CASES['static_neighbors']
        document = build(metadata['fixture'])
        gates = [row for row in metadata['cases'] if row['family'] == 'gate']
        self.assertEqual(96, len(gates))
        self.assertEqual(12, len(set(row['name'] for row in gates)))
        self.assertEqual(len(metadata['cases']), len(set(row['id'] for row in metadata['cases'])))
        for row in gates:
            with self.subTest(case=row['id']):
                properties = registry.states(foreground(document.get(row['keep'])))
                self.assertEqual(row['direction'], properties['minecraft:cardinal_direction'])
                self.assertEqual(row['open'], properties['open_bit'])
                self.assertEqual(row['in_wall'], properties['in_wall_bit'])
                self.assertNotEqual(AIR, foreground(document.get(row['occupied'])))
                self.assertEqual(3, len(row['camera']['offset']))
                self.assertTrue(all(foreground(document.get(pos)) != AIR for pos in row['cells']))

    def test_chorus_cells_have_all_six_faces_and_cross_chunk_control(self):
        metadata = VISUAL_CASES['static_neighbors']
        document = build(metadata['fixture'])
        rows = [row for row in metadata['cases'] if row['family'] == 'chorus']
        self.assertEqual(2, len(rows))
        for row in rows:
            center = row['keep']
            offsets = {tuple(pos[i] - center[i] for i in range(3)) for pos in row['cells']}
            self.assertEqual({(0, 0, 0), (-1, 0, 0), (1, 0, 0), (0, -1, 0),
                              (0, 1, 0), (0, 0, -1), (0, 0, 1)}, offsets)
            self.assertEqual('minecraft:chorus_flower', foreground(document.get((center[0], center[1] + 1, center[2])))[0])
            self.assertEqual('minecraft:end_stone', foreground(document.get((center[0], center[1] - 2, center[2])))[0])
        boundary = next(row for row in rows if row['id'].endswith('cross_chunk'))
        self.assertNotEqual(tuple(v >> 4 for v in boundary['keep']), tuple(v >> 4 for v in boundary['occupied']))

    def test_hanging_moss_has_static_tip_states_and_vertical_chunk_control(self):
        metadata = VISUAL_CASES['static_neighbors']
        document = build(metadata['fixture'])
        rows = [row for row in metadata['cases'] if row['family'] == 'hanging_moss']
        self.assertEqual(2, len(rows))
        for row in rows:
            self.assertEqual([False, False, False, False, True],
                             [registry.states(foreground(document.get(pos)))['tip'] for pos in row['cells']])
            root = row['cells'][0]
            self.assertEqual('minecraft:stone', foreground(document.get((root[0], root[1] + 1, root[2])))[0])
        boundary = next(row for row in rows if row['id'].endswith('cross_chunk'))
        self.assertNotEqual(tuple(v >> 4 for v in boundary['keep']), tuple(v >> 4 for v in boundary['occupied']))


if __name__ == '__main__':
    unittest.main()
