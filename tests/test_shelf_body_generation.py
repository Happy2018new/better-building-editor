"""Shelf candidates preserve solid bounds and native atlas texels."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_shelf_resources_r17 import body_model, shelf_cubes, FRONTS, DIRECTIONS, WOODS


class ShelfBodyGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reference = json.loads((ROOT/'tools/data/shelf_body_java_1.21.9_reference.json').read_bytes())

    def test_backing_split_preserves_volume_and_avoids_zero_thickness(self):
        for front in FRONTS:
            cubes = shelf_cubes(self.reference, front)
            self.assertEqual(5, len(cubes))
            self.assertEqual(16*16*3+2*16*4*2,
                             sum(cube['size'][0]*cube['size'][1]*cube['size'][2] for cube in cubes))
            for cube in cubes:
                self.assertTrue(all(size > 0 for size in cube['size']))
                for axis, (low, high) in enumerate(((-16, 0), (0, 16), (11, 16))):
                    self.assertGreaterEqual(cube['origin'][axis], low)
                    self.assertLessEqual(cube['origin'][axis]+cube['size'][axis], high)

    def test_middle_front_selects_original_native_texels_without_resampling(self):
        for front in FRONTS:
            middle = shelf_cubes(self.reference, front)[1]
            self.assertEqual([-16, 4, 13], middle['origin'])
            expected = self.reference['models'][front]['elements'][0]['faces']['north']['uv']
            actual = middle['uv']['north']
            self.assertEqual([expected[0]*2, expected[1]*2], actual['uv'])
            self.assertEqual([16, 8], actual['uv_size'])
            for cube in shelf_cubes(self.reference, front):
                for face in cube['uv'].values():
                    for axis in range(2):
                        start, size = face['uv'][axis], face['uv_size'][axis]
                        self.assertTrue(0 <= start <= 32)
                        self.assertTrue(0 <= start+size <= 32)

    def test_direction_and_front_models_are_distinct_cell_centered_candidates(self):
        identities = set()
        for wood in WOODS:
            for front in FRONTS:
                for direction in DIRECTIONS:
                    data = body_model(self.reference, wood, front, direction)['netease:block_geometry']
                    identities.add(data['description']['identifier'])
                    self.assertEqual([-8, 8, 8], data['bones'][0]['pivot'])
                    self.assertEqual([0, DIRECTIONS.index(direction)*90, 0], data['bones'][0]['rotation'])
        self.assertEqual(240, len(identities))


if __name__ == '__main__':
    unittest.main()
