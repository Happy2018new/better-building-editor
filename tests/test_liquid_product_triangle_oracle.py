"""Keep the independent triangle oracle sensitive to plausible shader faults."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import verify_liquid_product_triangles as oracle


class LiquidTriangleOracleTests(unittest.TestCase):
    def mesh(self):
        path = ROOT / 'resource_pack/models/modern_projection/liquid/flowing_water_grey_mesh.json'
        return json.loads(path.read_bytes())['mesh'][0]

    def test_actual_mesh_has_outward_triangles_in_every_face_and_payload_slot(self):
        mesh = self.mesh()
        heights = (.2, .7, .9, .4)
        for slot in range(4):
            for face, normal in enumerate(oracle.FACE_NORMALS):
                vertices, triangles = oracle.selected_mesh(mesh, slot, face)
                self.assertEqual(4, len(vertices))
                points, unused_uv = oracle.face_vertices(face, heights)
                for first, second, third in triangles:
                    cross = oracle.cross(oracle.subtract(points[second], points[first]),
                                         oracle.subtract(points[third], points[first]))
                    self.assertGreater(oracle.dot(cross, normal), 0)

    def test_index_reversal_or_role_change_cannot_silently_change_expected_geometry(self):
        for change in ('indices', 'position', 'normal'):
            mesh = copy.deepcopy(self.mesh())
            if change == 'indices':
                mesh['indices'][0] = list(reversed(mesh['indices'][0]))
            elif change == 'position':
                mesh['vertices'][0]['pos'][0] = .125
            else:
                mesh['vertices'][0]['normal'] = [0, -1, 0]
            with self.subTest(change=change), self.assertRaises(ValueError):
                oracle.selected_mesh(mesh, 0, 0)

    def test_top_interior_uses_actual_triangles_not_a_bilinear_patch(self):
        heights = (.2, .4, .9, .6)
        vertices = oracle.project_vertices(0, heights)
        x, z = .75, .25
        depth, uv = oracle.sample_triangle(vertices, (.1 + .8 * x, .9 - .8 * z))
        triangular_height = .2 * (1 - x) + .4 * (x - z) + .9 * z
        bilinear_height = .2 * (1 - x) * (1 - z) + .4 * x * (1 - z) + .9 * x * z + .6 * (1 - x) * z
        self.assertAlmostEqual(.5 + .3 * (triangular_height - .5), depth)
        self.assertNotAlmostEqual(triangular_height, bilinear_height)
        for actual, expected in zip(uv, (x, z)):
            self.assertAlmostEqual(expected, actual)

    def test_internal_diagonal_remains_covered_instead_of_creating_an_oracle_hole(self):
        vertices = oracle.project_vertices(0, (.25, .5, .75, 1))
        sample = oracle.sample_triangle(vertices, (.5, .5))
        self.assertIsNotNone(sample)
        self.assertEqual((.5, .5), sample[1])

    def test_all_side_uvs_follow_absolute_height_and_retain_bottom_strip(self):
        heights = (.2, .4, .9, .7)
        for face in range(1, 5):
            points, uv = oracle.face_vertices(face, heights)
            self.assertEqual(((0, 1), (1, 1)), uv[:2])
            for point, texcoord in zip(points, uv):
                self.assertAlmostEqual(1 - point[1], texcoord[1])
            projected = oracle.project_vertices(face, heights)
            # Every side contains the same fixed low point beneath both endpoints.
            sample = oracle.sample_triangle(projected, (.5, .1 + .8 * .1))
            self.assertIsNotNone(sample)
            self.assertAlmostEqual(.9, sample[1][1])

    def test_orthographic_camera_preserves_physical_face_coordinates_for_ui_and_world(self):
        heights = (.2, .4, .9, .7)
        for ui in (False, True):
            for face in range(6):
                cell = (3, 1, 2)
                matrix = oracle.camera_matrix(face, cell, ui)
                points, unused_uv = oracle.face_vertices(face, heights)
                projected = oracle.project_vertices(face, heights)
                for point, expected in zip(points, projected):
                    local = tuple(cell[i] + point[i] - 2 for i in range(3))
                    entity = (-local[0], 1.5 - local[2], -local[1], 1) if ui else local + (1,)
                    clip = tuple(sum(matrix[column * 4 + row] * entity[column] for column in range(4))
                                 for row in range(4))
                    for actual, wanted in zip(tuple(.5 + .5 * value for value in clip[:3]), expected[:3]):
                        self.assertAlmostEqual(wanted, actual)

    def test_marker_texels_distinguish_horizontal_flip_and_incorrect_low_side_stretch(self):
        background = (0, 0, 0, 1)
        actual = oracle.expected_pixel((.5, (.15, .8)), 'marker', 32, False, True, 0, background)
        wrong_flip = oracle.expected_pixel((.5, (.85, .8)), 'marker', 32, False, True, 0, background)
        wrong_stretch = oracle.expected_pixel((.5, (.15, .2)), 'marker', 32, False, True, 0, background)
        self.assertNotEqual(actual, wrong_flip)
        self.assertNotEqual(actual, wrong_stretch)
        self.assertGreater(actual[3], 0)

    def test_top_rotation_matches_four_independent_cardinal_fixture_positions(self):
        for code, expected in ((0, (.25, .25)), (64, (.25, .75)),
                               (128, (.75, .75)), (192, (.75, .25))):
            actual = oracle.ideal_top_uv((0, 0), code)
            for value, wanted in zip(actual, expected):
                self.assertAlmostEqual(wanted, value)

    def test_hidden_surface_retains_background_even_if_geometry_covers_pixel(self):
        background = (.2, .4, .6, 1)
        covered = (.5, (.5, .5))
        for mode in ('geometry', 'marker'):
            self.assertEqual((51, 102, 153, 255), oracle.expected_pixel(
                covered, mode, 32, False, True, 0, background, visible=False))

    def test_sensitivity_controls_change_actual_indices_or_shader_without_changing_oracle(self):
        fixture = {'name': '1/slot0/(64, 64, 64, 64)/r0/True'}
        original = {'name': 'product_water/100/marker/face1/slot0',
                    'vertex': 'liquidUv=vec2(u,1.0-height);',
                    'indices': [(0, 2, 1), (0, 3, 2)], 'fixtures': [fixture]}
        controls = oracle.sensitivity_cases([original])
        self.assertEqual(3, len(controls))
        self.assertEqual([(1, 2, 0), (2, 3, 0)], controls[0]['indices'])
        self.assertIn('1.0-v', controls[1]['vertex'])
        self.assertIn('1.0-u', controls[2]['vertex'])
        self.assertTrue(all(control['fixtures'] == original['fixtures'] for control in controls))
        self.assertEqual('liquidUv=vec2(u,1.0-height);', original['vertex'])


if __name__ == '__main__':
    unittest.main()
