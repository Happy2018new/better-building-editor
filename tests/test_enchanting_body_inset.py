"""A neighboring table bottom must not survive in the support's context tile."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
sys.path.insert(0, str(ROOT/'behavior_pack/modern_projection'))
from generate_enchanting_body_r17 import BOTTOM_INSETS, body_cube
from projection.render_layout import local_context_position


def visible_in_tile(point):
    phase = tuple((axis+.5) % 4. for axis in point)
    return all(.9999 <= axis <= 2.0001 for axis in phase)


class TableBottomInsetTests(unittest.TestCase):
    def test_original_bottom_reproduces_upper_neighbor_residue(self):
        encoded = local_context_position((3, 2, 3), (0, 1, 0))
        bottom = (encoded[0], encoded[1]-.5, encoded[2])
        self.assertTrue(visible_in_tile(bottom))

    def test_each_diagnostic_inset_rejects_neighbor_bottom_and_keeps_owner(self):
        for inset in BOTTOM_INSETS[1:]:
            cube = body_cube(inset)
            self.assertEqual(12., cube['origin'][1]+cube['size'][1])
            self.assertEqual({'up', 'down', 'north', 'south', 'east', 'west'}, set(cube['uv']))
            self.assertEqual(body_cube()['uv'], cube['uv'])
            for target in ((0, 0, 0), (3, 2, 3), (15, 15, 15), (16, 16, 16)):
                for neighbor, expected in (((0, 0, 0), True), ((0, 1, 0), False)):
                    encoded = local_context_position(target, neighbor)
                    bottom = (encoded[0], encoded[1]-.5+inset/16., encoded[2])
                    self.assertEqual(expected, visible_in_tile(bottom), (inset, target, neighbor))

    def test_bottom_only_inset_does_not_claim_horizontal_boundary_fix(self):
        for neighbor, axis, edge in (((1, 0, 0), 0, -.5),
                                     ((-1, 0, 0), 0, .5),
                                     ((0, 0, 1), 2, -.5),
                                     ((0, 0, -1), 2, .5)):
            encoded = local_context_position((3, 3, 3), neighbor)
            face = [encoded[0], encoded[1]-.125, encoded[2]]
            face[axis] += edge
            self.assertTrue(visible_in_tile(face), (neighbor, face))
        encoded = local_context_position((3, 3, 3), (0, -1, 0))
        self.assertFalse(visible_in_tile((encoded[0], encoded[1]+.25, encoded[2])))


if __name__ == '__main__':
    unittest.main()
