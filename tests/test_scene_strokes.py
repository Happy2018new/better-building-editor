import math
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.scene_lines import clip_stroke, segment_fractions


class SceneStrokeTests(unittest.TestCase):
    def test_rotated_quad_and_native_raster_margin_stay_inside_viewport(self):
        rng = random.Random(70)
        for unused in range(1500):
            width, height = rng.uniform(2, 600), rng.uniform(2, 400)
            a, b = [tuple(rng.uniform(-700, 700) for axis in range(2)) for end in range(2)]
            thickness = rng.uniform(.22, 2)
            segment = clip_stroke(a, b, width, height, thickness)
            if segment is None:
                continue
            dx, dy = b[0]-a[0], b[1]-a[1]
            length = math.hypot(dx, dy)
            normal = (-dy/length*thickness/2., dx/length*thickness/2.)
            for point in segment:
                for sign in (-1, 1):
                    for axis, extent in enumerate((width, height)):
                        corner = point[axis] + sign*normal[axis]
                        self.assertGreaterEqual(corner, 1.-1e-8)
                        self.assertLessEqual(corner, extent-1.+1e-8)

    def test_interior_points_are_not_shifted_or_shortened(self):
        a, b = (20., 40.), (70., 80.)
        self.assertEqual((a, b), clip_stroke(a, b, 100, 100, 1))

    def test_clipped_spectrum_keeps_original_vertex_field(self):
        a, b = (-50., 25.), (150., 75.)
        segment = clip_stroke(a, b, 100, 100, .65)
        for t, point in zip(segment_fractions(a, b, segment), segment):
            self.assertGreater(t, 0.)
            self.assertLess(t, 1.)
            for axis in range(2):
                self.assertAlmostEqual(point[axis], a[axis]+t*(b[axis]-a[axis]))

    def test_empty_or_too_narrow_viewport_has_no_stroke(self):
        self.assertIsNone(clip_stroke((0, 0), (0, 0), 100, 100, 1))
        self.assertIsNone(clip_stroke((0, 0), (100, 0), 100, .5, 1))
        self.assertIsNone(clip_stroke((-10, -10), (-5, -5), 100, 100, 1))
