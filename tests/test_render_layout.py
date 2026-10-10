import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'behavior_pack/modern_projection'))
from projection.render_layout import (CONTEXT_BASE, CONTEXT_STRIDE, MAX_LOGICAL_HEIGHT,
                                      OVERLAY_BASE, context_center, context_position,
                                      logical_position, overlay_index, overlay_position)


class RenderLayoutTests(unittest.TestCase):
    def test_real_vertices_and_maximum_top_are_not_classified_as_virtual(self):
        for y in (0., 16., MAX_LOGICAL_HEIGHT):
            pos = (128., y, 64.)
            self.assertEqual(pos, logical_position(pos))
            self.assertTrue(context_center(pos))
        self.assertGreater(OVERLAY_BASE, MAX_LOGICAL_HEIGHT)
        self.assertGreater(CONTEXT_BASE, OVERLAY_BASE + MAX_LOGICAL_HEIGHT)

    def test_overlay_vertices_decode_without_moving_x_or_z(self):
        for pos in ((0., 0., 0.), (2.5, 16.125, 7.25), (128., 128., 128.)):
            self.assertEqual(pos, logical_position(overlay_position(pos)))
        self.assertEqual(OVERLAY_BASE * 15 + 104, overlay_index(104, (3, 5, 7)))

    def test_context_center_and_neighbor_vertices_recover_logical_positions(self):
        for pos in ((0, 0, 0), (7, 15, 3), (127, 127, 127)):
            for neighbor in ((0, 0, 0), (1, 0, 0), (-1, -1, -1), (1, 1, 1)):
                encoded = context_position(pos, neighbor)
                for fraction in (0.125, 0.5, 0.875):
                    vertex = tuple(axis + fraction for axis in encoded)
                    expected = tuple(pos[axis] + neighbor[axis] + fraction for axis in range(3))
                    self.assertEqual(expected, logical_position(vertex))
                    self.assertEqual(neighbor == (0, 0, 0), context_center(vertex))
        self.assertEqual(CONTEXT_BASE + CONTEXT_STRIDE * 15 + 1,
                         context_position((7, 15, 3))[1])


if __name__ == '__main__':
    unittest.main()
