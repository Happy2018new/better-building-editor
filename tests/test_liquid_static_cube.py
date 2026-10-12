"""The remote opaque witness cannot silently alter the source neighborhood."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from liquid_static_cube_epochs import CUBE_NATIVE, CUBE_ORIGIN, add_cube
from audit_liquid_static_cube_low import clearance


class StaticCubeTests(unittest.TestCase):
    def source(self, liquid=(6, 96, 6)):
        water = [(liquid, ['minecraft:water', 0])]
        return {'platform': (4, 94, 3), 'cavity': [liquid], 'reserved': [liquid],
                'source_neighbor_context_changed': False,
                'controls': {name: {'cells': copy.deepcopy(water) if 'positive' in name or name == 'liquid_only' else [],
                                    'native_cells': []}
                             for name in ('supported_positive', 'supported_negative', 'liquid_only', 'empty')}}

    def test_same_cube_in_all_controls_and_source_cells_remain_exact(self):
        source = self.source()
        original = copy.deepcopy(source)
        result = add_cube(source, lambda rows: copy.deepcopy(rows))
        self.assertEqual(original, source)
        for name, row in result['controls'].items():
            self.assertIn((CUBE_ORIGIN, CUBE_NATIVE), row['cells'])
            self.assertEqual(original['controls'][name]['cells'],
                             [cell for cell in row['cells'] if tuple(cell[0]) != CUBE_ORIGIN])
        self.assertFalse(result['source_neighbor_context_changed'])
        self.assertGreaterEqual(result['opaque_same_alias_cube']['minimum_source_chebyshev_distance'], 2)
        self.assertEqual(27, len(set(result['reserved']) - set(source['reserved'])))

    def test_cube_adjacency_or_overlap_is_rejected_before_world_writes(self):
        for liquid in ((8, 96, 4), CUBE_ORIGIN):
            with self.assertRaises(ValueError):
                add_cube(self.source(liquid), lambda rows: rows)

    def test_existing_control_cell_cannot_be_overwritten(self):
        source = self.source()
        source['controls']['empty']['cells'].append((CUBE_ORIGIN, ['minecraft:stone', 0]))
        with self.assertRaises(ValueError):
            add_cube(source, lambda rows: rows)

    def test_native_footprint_clearance_accepts_both_face_windings(self):
        corners = np.array(((0., 0.), (4., 0.), (4., 4.), (0., 4.)))
        pixels = np.array(((1., 1.), (3., 1.), (3., 3.), (1., 3.)))
        self.assertEqual(1., clearance(pixels, corners))
        self.assertEqual(1., clearance(pixels, corners[::-1]))

    def test_native_footprint_crossing_a_face_boundary_is_rejected(self):
        corners = np.array(((0., 0.), (4., 0.), (4., 4.), (0., 4.)))
        with self.assertRaises(ValueError):
            clearance(np.array(((1., 1.), (4.01, 1.))), corners)


if __name__ == '__main__':
    unittest.main()
