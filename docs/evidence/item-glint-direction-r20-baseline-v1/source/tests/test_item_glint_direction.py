"""Direction gates distinguish signed phase motion from visible animation."""
from pathlib import Path
import sys
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_item_glint_direction_r20 import (brightness_comparison, direction_comparison, fit, layers,
                                            model, residual)


class GlintDirectionTests(unittest.TestCase):
    def setUp(self):
        self.parameters = np.array((.086824, .492404, .133333, .1662,
                                    .469846, -.171010, -.363636, .2062))

    def test_layer_permutation_preserves_both_velocities(self):
        reference = layers(self.parameters)
        comparison = direction_comparison(reference[::-1], reference)
        self.assertTrue(comparison['passed'])
        self.assertEqual([1, 0], comparison['reference_layer_order'])

    def test_time_reversal_wrong_uv_rotation_and_half_speed_are_rejected(self):
        reference = layers(self.parameters)
        reversed_time = self.parameters.copy()
        reversed_time[[2, 6]] *= -1.
        self.assertFalse(direction_comparison(layers(reversed_time), reference)['passed'])
        rotated = self.parameters.copy()
        for offset in (0, 4):
            rotated[offset:offset + 2] = (-rotated[offset + 1], rotated[offset])
        self.assertFalse(direction_comparison(layers(rotated), reference)['passed'])
        slowed = self.parameters.copy()
        slowed[[2, 6]] *= .5
        self.assertFalse(direction_comparison(layers(slowed), reference)['passed'])

    def test_native_texture_fit_recovers_known_motion_on_withheld_pixels(self):
        path = ROOT / 'resource_pack/textures/models/modern_projection/item_icons/enchanted_glint.png'
        with Image.open(path) as image:
            texture = np.asarray(image.convert('RGB'))[0, :, 0].astype(float) / 255.
        uv = np.random.default_rng(17).uniform(.05, .95, (105, 2))
        times = np.linspace(0., 8., 81)
        signal = model(self.parameters, uv - .5, times, texture)
        samples = np.repeat((60. + signal * 20.)[:, :, None], 3, axis=2)
        measured = fit({'uv': uv, 'times': times, 'samples': samples}, texture)
        self.assertTrue(measured['fit_valid'])
        self.assertLess(measured['nrmse'], .005)
        self.assertLess(measured['training_frames'], measured['frames'])
        self.assertLess(measured['training_uv_samples'], measured['uv_samples'])
        self.assertTrue(direction_comparison(measured['layers'], layers(self.parameters))['passed'])
        observed = samples[:, :, 0] - samples[:, :, 0].mean(axis=0)
        correct = residual(self.parameters, uv - .5, times, observed, texture)
        backwards = residual(self.parameters, uv - .5, times, observed[::-1], texture)
        self.assertLess(np.mean(correct ** 2), .000001)
        self.assertGreater(np.mean(backwards ** 2), 1.)

    def test_brightness_gate_rejects_overbright_or_invisible_dynamic_layers(self):
        reference = {'fit_valid': True, 'rgb_temporal_gains': [20., 5., 50.]}
        self.assertTrue(brightness_comparison(reference, reference)['passed'])
        for gains in ([36., 9., 80.], [10., 2.5, 25.]):
            changed = dict(reference, rgb_temporal_gains=gains)
            self.assertFalse(brightness_comparison(changed, reference)['passed'])
        self.assertFalse(brightness_comparison(dict(reference, fit_valid=False), reference)['passed'])


if __name__ == '__main__':
    unittest.main()
