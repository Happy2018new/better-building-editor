"""Opaque witnesses change across epochs while unchanged scene controls remain stable."""
import copy
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_liquid_static_cube_r12 import cube_stability, measure_cube
from liquid_static_coordinate_epochs import frame


class CubeR12Tests(unittest.TestCase):
    def epochs(self):
        epochs = {}
        for epoch, value in (('low', 12.), ('high', 192.), ('coordinate', 62.), ('complement', 142.)):
            row = {'id': '0/north', 'camera': {'position': [4, 98.5, 3]},
                'native_size': [1994, 1105], 'calibration_fov': 66.1,
                'host_bilinear_weights': [[.25] * 4],
                'observations': {name: [[value] * 3] for name in
                                 ('supported_positive', 'supported_negative', 'liquid_only', 'empty')},
                'native_observations': {name: [[[value] * 3] * 4] for name in
                                        ('supported_positive', 'supported_negative', 'liquid_only', 'empty')}}
            epochs[epoch] = [row]
        return epochs

    def limits(self):
        return {'minimum_green_blue_reference_spread': 40., 'minimum_red_reference_spread': 8.,
                'maximum_dry_control_rmse': 3., 'maximum_complement_source_rmse': 3.}

    def test_intended_cube_epoch_changes_are_not_dry_scene_failures(self):
        row = cube_stability(self.epochs(), self.limits())['0/north']
        self.assertTrue(row['passed'])
        self.assertEqual(0., row['maximum_within_epoch_control_native_rgb_rmse'])

    def test_cube_change_between_scene_controls_fails_before_uv_claim(self):
        epochs = self.epochs()
        epochs['coordinate'][0]['native_observations']['empty'][0][2] = [22., 22., 22.]
        row = cube_stability(epochs, self.limits())['0/north']
        self.assertFalse(row['passed'])
        self.assertGreater(row['maximum_within_epoch_control_native_rgb_rmse'], 3.)

    def test_complement_drift_and_camera_change_remain_failures(self):
        for field in ('observations', 'camera'):
            epochs = copy.deepcopy(self.epochs())
            if field == 'observations':
                epochs['complement'][0][field]['supported_positive'] = [[172.] * 3]
            else:
                epochs['complement'][0][field]['position'][0] = 5
            self.assertFalse(cube_stability(epochs, self.limits())['0/north']['passed'])

    def test_exact_prediction_does_not_identify_equivalent_samplers(self):
        u, height = np.meshgrid(np.linspace(.12, .77, 14), np.linspace(.12, .88, 16))
        u, height = u.ravel(), height.ravel()
        offsets = np.array((-.0005, .0005, -.0003, .0003))
        pu, ph = (u[:, None] + offsets).ravel(), (height[:, None] + offsets).ravel()
        grid = {'u': pu, 'height': ph, 'top': np.ones_like(pu)}
        pixels = frame('coordinate')[:, :, :3]
        texture = pixels[np.floor((1 - ph) * 16).astype(int), np.floor(pu * 16).astype(int)]
        texture = texture.astype(float).reshape(-1, 4, 3)
        low = np.full_like(texture, 12.)
        spread = np.full_like(texture, 180.)
        weights = np.tile([.1, .2, .3, .4], (len(u), 1))
        values = {'low': low, 'high': low + spread,
                  'coordinate': low + (texture - 16) / 224 * spread,
                  'complement': low + (240 - texture) / 224 * spread}
        epochs = {epoch: [] for epoch in values}
        for depth in (0, 1, 3):
            for epoch, observed in values.items():
                sampled = np.sum(observed * weights[:, :, None], axis=1)
                epochs[epoch].append({'id': str(depth) + '/north',
                    'role': 'training' if depth == 0 else 'holdout', 'native_grid': grid,
                    'quad_grids': [grid] * 4, 'host_bilinear_weights': weights,
                    'native_observations': {name: observed for name in
                        ('supported_positive', 'supported_negative', 'liquid_only', 'empty')},
                    'observations': {name: sampled for name in
                        ('supported_positive', 'supported_negative', 'liquid_only', 'empty')},
                    'camera': 'identical', 'native_size': [1994, 1105], 'calibration_fov': 66.1})
        limits = dict(self.limits(), maximum_rgb_rmse=3., minimum_explained_variance=.9,
                      minimum_texture_rms=2., minimum_property_margin_rmse=.5)
        result = measure_cube(epochs, {'limits': limits})
        self.assertLess(result['training_rgb_rmse'], 1e-12)
        self.assertEqual('bottom', result['selected']['side_v'])
        self.assertFalse(result['identification']['sampler']['identified'])
        self.assertFalse(result['cube_spatial_candidate_observed'])
        self.assertFalse(result['native_uv_accepted'])


if __name__ == '__main__':
    unittest.main()
