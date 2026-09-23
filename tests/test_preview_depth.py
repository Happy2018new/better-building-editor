"""Shared view-space depth must agree on both sides of a chunk boundary."""
import itertools
import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'behavior_pack/HelloScript'))
from projection.preview_depth import depth_color, tile_layer
from projection.biomes import KEYS
from projection.camera import OrbitCamera


def decode(rgb):
    r, g, b = (round(v*255) for v in rgb)
    return r-208, (g*256+b-32768)/64.


class PreviewDepthTests(unittest.TestCase):
    def test_distance_and_biome_roundtrip(self):
        for biome in KEYS:
            for distance in (-200.125, -64.507, -16.001, -8.5, -.001, 0, 8.5, 155.99):
                rgb = depth_color(distance, biome)
                index, actual = decode(rgb)
                self.assertEqual(KEYS.index(biome)+1, index)
                self.assertLessEqual(abs(actual-distance), 1./128.+1e-8)
                self.assertTrue(all(0 <= v <= 1 for v in rgb))

    def test_exact_building_fits_without_clamping_at_all_view_angles(self):
        size = (64,128,64)
        for yaw, pitch, depth in itertools.product(range(0,361,45),(-89,-45,0,45,89),(0,32,128)):
            camera = OrbitCamera(yaw,pitch)
            toward = camera.basis()[2]
            plane = sum(size[i]*max(0,toward[i]) for i in range(3))+.5-depth
            for point in itertools.product((0,64),(0,128),(0,64)):
                distance = sum(point[i]*toward[i] for i in range(3))-plane
                self.assertLessEqual(abs(decode(depth_color(distance,KEYS[0]))[1]-distance),1./128.+1e-8)

    def test_neighbouring_tiles_agree_on_the_same_surface_point(self):
        point = (16.,20.,10.)
        centers = ((8.,24.,8.),(24.,24.,8.))
        for yaw in (0,1,89,90,91,179,180,181,269,270,271,359):
            toward = OrbitCamera(yaw,30).basis()[2]
            for plane in (-30.,0.,60.,128.):
                values = []
                for center in centers:
                    distance = sum(center[i]*toward[i] for i in range(3))-plane
                    values.append(decode(depth_color(distance,KEYS[0]))[1] +
                                  sum((point[i]-center[i])*toward[i] for i in range(3)))
                self.assertLessEqual(abs(values[0]-values[1]),1./64.+1e-8)

    def test_fixed_draw_pairs_do_not_overlap_each_other_or_overlays(self):
        layers = sorted(tile_layer(k) for k in itertools.product(range(4),range(8),range(4)))
        self.assertEqual(128,len(set(layers)))
        self.assertTrue(all(layers[i]+1 < layers[i+1]+1 for i in range(127)))
        self.assertEqual(50,layers[0])
        self.assertLess(layers[-1],360)
        self.assertEqual(256,len(set(layers+[v-1 for v in layers])))


if __name__ == '__main__':unittest.main()
