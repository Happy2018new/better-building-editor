"""Synthetic projection checks establish mathematics, not native liquid facts."""
from copy import deepcopy
import math
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from camera_projection import project_points
from measure_native_liquid_surface import CORNERS, analyze_cell, measure_height, pixel_viewport

CAMERA = {'position': (-5., 4., -7.), 'target': (.5, .5, .5),
          'screen': (1994, 1105), 'vertical_fov': 67.8, 'roll': 7.}


def projected(camera, point):
    result, = project_points((point,), camera['position'], camera['target'], camera['screen'],
                             camera['vertical_fov'], camera.get('roll', 0.))
    scale = pixel_viewport(camera)['scale']
    return (result['screenX'] * scale[0], result['screenY'] * scale[1])


def input_cell(heights):
    return {'camera': deepcopy(CAMERA), 'cell_origin': (0., 0., 0.), 'declared_pixel_budget': 0.,
            'source': {'fixture': 'test.layers.liquids', 'case_id': 'synthetic_math_only'},
            'observations': [{'corner': corner, 'pixel': projected(CAMERA, (corner[0], height, corner[1])),
                              'visibility': 'visible_boundary', 'source': 'synthetic explicit corner'}
                             for corner, height in zip(CORNERS, heights)]}


class NativeLiquidHeightMathTests(unittest.TestCase):
    def test_actual_native_xy_scale_roundtrips_without_changing_engine_fov(self):
        camera = dict(CAMERA, screen=(499., 277.), native_image_screen=(1994, 1105))
        expected = pixel_viewport(camera)
        self.assertEqual((1994 / 499., 1105 / 277.), expected['scale'])
        self.assertNotEqual(expected['scale'][0], expected['scale'][1])
        for corner, height in zip(CORNERS, (.19, .81, .37, .63)):
            with self.subTest(corner=corner):
                pixel = projected(camera, (corner[0], height, corner[1]))
                result = measure_height(camera, corner, 0., pixel, 0.)
                self.assertEqual('diagnostic', result['status'])
                self.assertAlmostEqual(height, result['height_estimate'], places=10)
                self.assertLess(result['reprojection_error_pixels'], 1e-8)
                self.assertEqual('native_png_pixels', result['declared_pixel_budget_units'])
                self.assertFalse(result['pixel_viewport']['capture_binding_verified'])

    def test_anisotropic_native_disk_interval_stays_exactly_three_png_pixels(self):
        camera = dict(CAMERA, screen=(499., 277.), native_image_screen=(1800, 800))
        center = projected(camera, (0., .41, 0.))
        first, last = projected(camera, (0., 0., 0.)), projected(camera, (0., 1., 0.))
        line = tuple(last[i] - first[i] for i in range(2))
        length = math.hypot(*line)
        shifted = (center[0] - 2. * line[1] / length, center[1] + 2. * line[0] / length)
        result = measure_height(camera, (0., 0.), 0., shifted, 3.)
        self.assertEqual('native_png_pixels', result['declared_pixel_budget_units'])
        self.assertAlmostEqual(2., result['perpendicular_residual_pixels'], places=8)
        self.assertAlmostEqual(.41, result['height_estimate'], places=8)
        for height in result['height_interval']:
            self.assertAlmostEqual(3., math.dist(shifted, projected(camera, (0., height, 0.))), places=8)

    def test_absent_mapping_and_equal_scale_preserve_previous_engine_math(self):
        pixel = projected(CAMERA, (0., .41, 0.))
        previous = measure_height(CAMERA, (0., 0.), 0., pixel, 3.)
        self.assertEqual('engine_pixels', previous['declared_pixel_budget_units'])
        identity = measure_height(dict(CAMERA, native_image_screen=CAMERA['screen']),
                                  (0., 0.), 0., pixel, 3.)
        scaled_camera = dict(CAMERA, native_image_screen=tuple(value * 4 for value in CAMERA['screen']))
        scaled = measure_height(scaled_camera, (0., 0.), 0., tuple(value * 4 for value in pixel), 12.)
        for result in (identity, scaled):
            self.assertAlmostEqual(previous['height_estimate'], result['height_estimate'], places=10)
            for index in (0, 1):
                self.assertAlmostEqual(previous['height_interval'][index], result['height_interval'][index], places=10)

    def test_native_viewport_bounds_use_png_dimensions_and_invalid_mapping_is_rejected(self):
        camera = dict(CAMERA, screen=(499., 277.), native_image_screen=(1994, 1105))
        pixel = projected(camera, (0., .4, 0.))
        self.assertGreater(pixel[0], camera['screen'][0])
        self.assertEqual('diagnostic', measure_height(camera, (0., 0.), 0., pixel, 0.)['status'])
        self.assertEqual('pixel_outside_viewport', measure_height(camera, (0., 0.), 0., (1994., 10.), 3.)['reason'])
        for dimensions in ((0, 1105), (-1, 1105), (1994, float('nan')), (1994, float('inf')), (1994,)):
            with self.subTest(dimensions=dimensions), self.assertRaises(ValueError):
                measure_height(dict(camera, native_image_screen=dimensions), (0., 0.), 0., pixel, 3.)

    def test_contained_or_asserted_source_metadata_cannot_promote_mathematics_to_accuracy(self):
        data = input_cell((.2, .4, .6, .8))
        data['source'].update(context_changed=True, public_controls_eligible=True, native_geometry_accepted=True,
                              accuracy_accepted=True, source_snapshot_binding_verified=True)
        result = analyze_cell(data)
        self.assertTrue(result['four_corners_observed'])
        self.assertTrue(result['context_changed'])
        self.assertFalse(result['accuracy_accepted'])
        self.assertFalse(result['public_controls_eligible'])
        self.assertFalse(result['native_geometry_accepted'])
        self.assertFalse(result['limits']['source_snapshot_binding_verified'])
        self.assertFalse(result['limits']['viewport_capture_binding_verified'])
        data['observations'] = []
        result = analyze_cell(data)
        self.assertEqual(list(CORNERS), result['unobservable_corners'])
        self.assertFalse(result['four_corners_observed'])

    def test_nonflat_four_heights_roundtrip_with_perspective_and_roll(self):
        heights = (.19, .81, .37, .63)
        result = analyze_cell(input_cell(heights))
        self.assertTrue(result['four_corners_observed'])
        self.assertFalse(result['native_geometry_accepted'])
        for row, expected in zip(result['corners'], heights):
            self.assertEqual('diagnostic', row['status'])
            self.assertAlmostEqual(expected, row['height_estimate'], places=10)
            self.assertAlmostEqual(expected, row['height_interval'][0], places=10)
            self.assertAlmostEqual(expected, row['height_interval'][1], places=10)
            self.assertLess(row['reprojection_error_pixels'], 1e-8)
            self.assertFalse(row['accuracy_accepted'])

    def test_declared_pixel_disk_maps_to_a_correct_height_interval(self):
        pixel = projected(CAMERA, (0., .41, 0.))
        result = measure_height(CAMERA, (0., 0.), 0., pixel, 3.)
        lower, upper = result['height_interval']
        self.assertLess(lower, .41)
        self.assertGreater(upper, .41)
        for height in (lower, upper):
            boundary = projected(CAMERA, (0., height, 0.))
            self.assertAlmostEqual(3., math.dist(pixel, boundary), places=8)
        self.assertFalse(result['camera_uncertainty_included'])
        self.assertEqual('declared_pixel_budget_only', result['interval_scope'])
        self.assertFalse(result['accuracy_accepted'])

    def test_wrong_lateral_xz_is_rejected_by_perpendicular_residual(self):
        pixel = projected(CAMERA, (0., .4, 0.))
        result = measure_height(CAMERA, (1., 0.), 0., pixel, 3.)
        self.assertEqual('unobservable', result['status'])
        self.assertEqual('pixel_inconsistent_with_known_xz', result['reason'])

    def test_perpendicular_pixel_error_consumes_the_interval_budget(self):
        center = projected(CAMERA, (0., .41, 0.))
        first, last = projected(CAMERA, (0., 0., 0.)), projected(CAMERA, (0., 1., 0.))
        line = tuple(last[i] - first[i] for i in range(2))
        length = math.hypot(*line)
        shifted = (center[0] - 2. * line[1] / length, center[1] + 2. * line[0] / length)
        result = measure_height(CAMERA, (0., 0.), 0., shifted, 3.)
        self.assertAlmostEqual(2., result['perpendicular_residual_pixels'], places=8)
        self.assertAlmostEqual(.41, result['height_estimate'], places=8)
        for height in result['height_interval']:
            boundary = projected(CAMERA, (0., height, 0.))
            self.assertAlmostEqual(3., math.dist(shifted, boundary), places=8)

    def test_wrong_depth_can_be_ambiguous_and_is_never_claimed_verified(self):
        camera = dict(CAMERA, position=(0., .5, 6.), target=(0., .5, 0.), roll=0.)
        pixel = projected(camera, (0., .7, 0.))
        result = measure_height(camera, (0., -1.), 0., pixel, 0.)
        self.assertEqual('diagnostic', result['status'])
        self.assertNotAlmostEqual(.7, result['height_estimate'])
        self.assertFalse(result['known_xz_verified_from_image'])
        self.assertFalse(result['accuracy_accepted'])

    def test_height_line_along_a_camera_ray_is_unobservable(self):
        camera = dict(CAMERA, position=(0., 3., 0.), target=(1., 0., 0.), roll=0.)
        result = measure_height(camera, (0., 0.), 0., projected(camera, (0., .5, 0.)), 3.)
        self.assertEqual('height_line_degenerate', result['reason'])

    def test_degenerate_camera_basis_is_unobservable(self):
        camera = dict(CAMERA, position=(0., 3., 0.), target=(0., 0., 0.), roll=0.)
        result = measure_height(camera, (0., 0.), 0., (997., 552.5), 3.)
        self.assertEqual('invalid_projection', result['reason'])

    def test_near_clipped_or_behind_camera_line_is_not_partially_fit(self):
        camera = dict(CAMERA, position=(0., .5, .02), target=(0., .5, -1.), roll=0.)
        for z in (0., .03):
            with self.subTest(z=z):
                result = measure_height(camera, (0., z), 0., (997., 552.5), 3.)
                self.assertEqual('height_line_near_clipped', result['reason'])

    def test_missing_occluded_and_unattributed_corners_are_not_filled(self):
        data = input_cell((.2, .4, .6, .8))
        data['observations'].pop()
        data['observations'][1]['visibility'] = 'occluded'
        del data['observations'][2]['source']
        result = analyze_cell(data)
        self.assertFalse(result['four_corners_observed'])
        self.assertEqual(3, len(result['unobservable_corners']))
        self.assertEqual(['boundary_visibility_not_established', 'observation_source_missing',
                          'no_explicit_observation'], [row['reason'] for row in result['corners'][1:]])
        self.assertTrue(all('height_estimate' not in row for row in result['corners'][1:]))

    def test_out_of_height_or_viewport_observations_are_rejected(self):
        result = measure_height(CAMERA, (0., 0.), 0., projected(CAMERA, (0., 1.2, 0.)), 3.)
        self.assertEqual('point_estimate_outside_unit_height', result['reason'])
        result = measure_height(CAMERA, (0., 0.), 0., (-1., 20.), 3.)
        self.assertEqual('pixel_outside_viewport', result['reason'])

    def test_nonfinite_or_negative_budget_and_duplicate_identity_fail(self):
        pixel = projected(CAMERA, (0., .4, 0.))
        for budget in (-1., float('nan'), float('inf')):
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                measure_height(CAMERA, (0., 0.), 0., pixel, budget)
        with self.assertRaises(ValueError):
            measure_height(CAMERA, (0., 0.), 0., (float('nan'), 0.), 3.)
        data = input_cell((.2, .4, .6, .8))
        data['observations'].append(data['observations'][0])
        with self.assertRaises(ValueError):
            analyze_cell(data)
        data['observations'] = []
        data['declared_pixel_budget'] = -1.
        with self.assertRaises(ValueError):
            analyze_cell(data)


if __name__ == '__main__':
    unittest.main()
