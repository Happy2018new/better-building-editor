"""Shelf candidates preserve solid bounds and native atlas texels."""
import json
from pathlib import Path
import sys
import unittest
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from generate_shelf_resources_r17 import body_model, shelf_cubes, FRONTS, DIRECTIONS, WOODS
from generate_shelf_direction_controls_r20 import baked_body_model, rotate_cubes_once


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

    def test_baked_turns_preserve_original_and_return_exact_uvs_after_full_rotation(self):
        for front in FRONTS:
            original = shelf_cubes(self.reference, front)
            saved = deepcopy(original)
            rotated = original
            for unused in range(4):
                rotated = rotate_cubes_once(rotated)
            self.assertEqual(saved, original)
            self.assertEqual(saved, rotated)

    def test_baked_front_moves_to_requested_world_face_with_unrotated_bones(self):
        front_bounds = {'north': (2, 13), 'east': (0, -13),
                        'south': (2, 3), 'west': (0, -3)}
        for front in FRONTS:
            for direction, (axis, coordinate) in front_bounds.items():
                model = baked_body_model(self.reference, front, direction, True)
                geometry = model['netease:block_geometry']
                bone = geometry['bones'][0]
                self.assertEqual([0, 0, 0], bone['rotation'])
                self.assertTrue(geometry['description']['use_ao'])
                middle = bone['cubes'][1]
                surface = middle['origin'][axis]
                if direction in ('east', 'south'):
                    surface += middle['size'][axis]
                self.assertEqual(coordinate, surface)
                self.assertEqual(shelf_cubes(self.reference, front)[1]['uv']['north'],
                                 middle['uv'][direction])
                self.assertEqual(16*16*3+2*16*4*2,
                                 sum(cube['size'][0]*cube['size'][1]*cube['size'][2]
                                     for cube in bone['cubes']))
                for cube in bone['cubes']:
                    for i, (low, high) in enumerate(((-16, 0), (0, 16), (0, 16))):
                        self.assertGreaterEqual(cube['origin'][i], low)
                        self.assertLessEqual(cube['origin'][i] + cube['size'][i], high)


if __name__ == '__main__':
    unittest.main()
