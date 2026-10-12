"""Independent static-epoch reference and raster-footprint regressions."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tools'))
import analyze_liquid_static_coordinates as analyze
import liquid_static_coordinate_epochs as assets
from measure_native_liquid_side_uv import Hypothesis, side_grid
from camera_projection import project_points


class StaticCoordinateTests(unittest.TestCase):
    def test_each_opaque_strip_has_identical_frames_and_complement_is_exact(self):
        first, second = assets.frame('coordinate'), assets.frame('complement')
        np.testing.assert_array_equal(first[:, :, :3].astype(int)+second[:, :, :3], np.full((32, 32, 3), 256))
        self.assertTrue(np.all(first[:, :, 3] == 255))
        self.assertTrue(np.all(second[:, :, 3] == 255))
        self.assertGreater(np.std(first[:, :, 1]), 60)

    def test_ray_plane_inverts_independent_world_projection_at_raster_centers(self):
        camera = {'position': [4., 98.5, 3.], 'target': [6.5, 96.5, 6.5], 'stable': {'screen': [499., 277.]}}
        surface = {'cell_origin': [6., 96., 6.], 'corner_heights': [.8]*4, 'side': 'north'}
        original = side_grid(surface['cell_origin'], surface['corner_heights'], 'north', [.2, .5, .8], [.3, .7])
        screen = project_points(original['world_points'], camera['position'], camera['target'], [499, 277], 66.6)
        pixels = np.array([[p['screenX']*1994/499-.5, p['screenY']*1105/277-.5] for p in screen])
        recovered = analyze.pixel_plane_grid(pixels, surface, camera, [1994, 1105], 66.6)
        np.testing.assert_allclose(recovered['u'], original['u'], atol=1e-13)
        np.testing.assert_allclose(recovered['height'], original['height'], atol=1e-13)

    def sequences(self):
        result = {epoch: [] for epoch in assets.EPOCHS}
        correct = Hypothesis('nw', 'bottom', 'identity', 1., False, 0., 'edges')
        pixels = assets.frame('coordinate')[:, :, :3]
        u, fraction = np.meshgrid(np.linspace(.12, .88, 16), np.linspace(.12, .88, 16))
        u, fraction = u.ravel(), fraction.ravel()
        for depth, top in ((0, .82), (1, .64), (3, .46)):
            height = fraction*top
            # Four source coordinates per host sample, independent direct texel addressing.
            offsets = np.array((-.0005, .0005, -.0003, .0003))
            pu = (u[:, None]+offsets).ravel()
            ph = (height[:, None]+offsets).ravel()
            grid = {'u': pu, 'height': ph, 'top': np.full_like(pu, top)}
            tx = np.clip(np.floor(pu*16).astype(int), 0, 31)
            ty = np.clip(np.floor((1-ph)*16).astype(int), 0, 31)
            texture = pixels[ty, tx].astype(float).reshape(-1, 4, 3)
            low = np.empty_like(texture)
            low[:, :, 0] = 12+u[:, None]*8
            low[:, :, 1] = 50+fraction[:, None]*70
            low[:, :, 2] = 40+u[:, None]*60
            spread = np.empty_like(texture)
            spread[:, :, 0] = 30
            spread[:, :, 1] = 90
            spread[:, :, 2] = 110
            weights = np.tile([.1, .2, .3, .4], (len(u), 1))
            coordinate = low+(texture-16)/224*spread
            complement = low+(240-texture)/224*spread
            values = {'low': low, 'high': low+spread, 'coordinate': coordinate, 'complement': complement}
            for epoch in assets.EPOCHS:
                shown = np.sum(values[epoch]*weights[:, :, None], axis=1)
                result[epoch].append({'id': str(depth), 'role': 'training' if depth == 0 else 'holdout',
                    'grid': {'u': u, 'height': height, 'top': np.full_like(u, top)},
                    'native_grid': grid, 'quad_grids': [grid]*4, 'host_bilinear_weights': weights,
                    'native_observations': {'supported_positive': values[epoch]},
                    'observations': {'supported_positive': shown, 'supported_negative': shown*0+40, 'empty': shown*0+220},
                    'camera': 'identical', 'native_size': [1994, 1105], 'calibration_fov': 66.6})
        return result

    def plan(self):
        return {'sample_control': 'supported_positive', 'limits': {'maximum_rgb_rmse': 3.,
            'minimum_explained_variance': .9, 'minimum_texture_rms': 2., 'minimum_property_margin_rmse': .5,
            'minimum_green_blue_reference_spread': 40., 'minimum_red_reference_spread': 8.,
            'maximum_dry_control_rmse': 3., 'maximum_complement_source_rmse': 3.}}

    def test_local_flat_references_recover_mapping_with_no_candidate_gain(self):
        result = analyze.measure(self.sequences(), self.plan())
        self.assertLess(result['training_rgb_rmse'], 1e-12)
        self.assertTrue(result['native_side_uv_observed'], result['identification'])
        self.assertEqual('nw', result['selected']['region'])
        self.assertEqual('height', Hypothesis(**result['selected']).v_basis)
        self.assertEqual('edges', result['selected']['pixel_mapping'])
        self.assertFalse(result['native_uv_accepted'])

    def test_changed_camera_or_backdrop_fails_even_with_perfect_texture(self):
        epochs = self.sequences()
        epochs['high'][1]['camera'] = 'changed'
        epochs['coordinate'][2]['observations']['empty'] += 4
        result = analyze.measure(epochs, self.plan())
        self.assertFalse(result['native_side_uv_observed'])
        self.assertFalse(result['stability']['1']['passed'])
        self.assertFalse(result['stability']['3']['passed'])

    def test_complement_change_cannot_be_fitted_away(self):
        epochs = self.sequences()
        epochs['complement'][1]['observations']['supported_positive'] += 12
        result = analyze.measure(epochs, self.plan())
        self.assertFalse(result['stability']['1']['passed'])
        self.assertFalse(result['sequences']['1']['passed'])
        self.assertFalse(result['native_side_uv_observed'])


if __name__ == '__main__':
    unittest.main()
