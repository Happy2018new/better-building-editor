"""Native water oracles reject changed sessions, frames, grids and stale pixels."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import water_native_projection as native
from analyze_water_acceptance_r16 import side_checks


CAMERA = {'position': [10., 20., 30.], 'rotation': [20., 35., 0.],
          'screen': [25., 25.], 'fov': 60.}
BINDING = {'id': 'session', 'owner': 'water', 'game_pid': 123,
           'game_identity': 'creation-time', 'session_file': 'owned/session.json'}


def readings(point_sets, origin=(3., 4., 5.)):
    reading = {'origin': list(origin), 'camera_position': CAMERA['position'],
        'camera_rotation': CAMERA['rotation'], 'screen': CAMERA['screen'], 'fov': CAMERA['fov'],
        'world_points': {}, 'projection': {}}
    for key, points in point_sets.items():
        reading['world_points'][key] = [(point[0] + origin[0], point[1] + origin[1], point[2] + origin[2])
                                       for point in points]
        reading['projection'][key] = [{'screenX': 20.5 + index % 10, 'screenY': 30.5 + index // 10,
            'isInScreen': True, 'depth': .1} for index in range(len(points))]
    return {'before': copy.deepcopy(reading), 'after': copy.deepcopy(reading)}


class NativeWaterProjectionTests(unittest.TestCase):
    def test_final_native_rejection_replaces_previously_passing_artifact(self):
        from verify_camera_projection import finalize_native_calibration
        evidence = {'passed': True, 'completed': True, 'restored': True,
            'native_projection': {'session_binding': BINDING, 'source_contract_sha256': 'source',
                                  'validation': {'old': 'passed'}}}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'calibration.json'
            output.write_text(json.dumps(evidence), encoding='ascii')
            with patch.object(native, 'validate_calibration', side_effect=ValueError('Wrong native PNG')):
                with self.assertRaisesRegex(ValueError, 'Wrong native PNG'):
                    finalize_native_calibration(evidence, output)
            recorded = json.loads(output.read_bytes())
            self.assertFalse(recorded['passed'])
            self.assertEqual('Wrong native PNG', recorded['native_projection']['validation_error'])
            self.assertNotIn('validation', recorded['native_projection'])

    def test_grid_keeps_original_sampling_and_declared_texel_centers(self):
        plan = native.grids()
        self.assertEqual(8, len(plan))
        self.assertEqual((14, 18), plan['original_south_3_3_4']['dimensions'])
        self.assertEqual((8, 12), plan['texel_centers_east_4_3_4']['dimensions'])
        np.testing.assert_allclose(plan['original_south_3_3_4']['points'][0], (3.88, 3.16, 5.))
        np.testing.assert_allclose(plan['texel_centers_east_4_3_4']['points'][0], (5., 3. + 10. / 15., 4. + 2. / 15.))

    def test_physical_pixel_samples_are_not_scaled_by_logical_ui_size(self):
        image = np.arange(100 * 100 * 3).reshape(100, 100, 3)
        record = readings({'one': [(0., 0., 0.)]})
        mapped = native.validate_readings(record, CAMERA, (3., 4., 5.), {'one': [(0., 0., 0.)]}, (100, 100))
        np.testing.assert_array_equal(native.sample(image, mapped['one'], (1, 1))[0, 0], image[30, 20])

    def test_changed_camera_origin_world_grid_and_point_drift_reject(self):
        points = {'one': [(0., 0., 0.)]}
        original = readings(points)
        mutations = (
            ('camera_position', [11., 20., 30.]), ('origin', [4., 4., 5.]),
            ('world_points', {'one': [(3., 4., 6.)]}),
            ('projection', {'one': [{'screenX': 21., 'screenY': 30.5, 'isInScreen': True}]}))
        for key, value in mutations:
            with self.subTest(key=key):
                record = copy.deepcopy(original)
                record['after'][key] = value
                with self.assertRaises(ValueError):
                    native.validate_readings(record, CAMERA, (3., 4., 5.), points, (100, 100))

    def test_nonfinite_offscreen_wrong_grid_and_double_ui_scaling_reject(self):
        points = {'one': [(0., 0., 0.)]}
        for point in ({'screenX': float('nan'), 'screenY': 30., 'isInScreen': True},
                      {'screenX': 20., 'screenY': 30., 'isInScreen': False},
                      {'screenX': 120., 'screenY': 120., 'isInScreen': True}):
            with self.subTest(point=point):
                record = readings(points)
                record['before']['projection']['one'] = record['after']['projection']['one'] = [point]
                with self.assertRaises(ValueError):
                    native.validate_readings(record, CAMERA, (3., 4., 5.), points, (100, 100))
        record = readings(points)
        record['after']['projection']['extra'] = []
        with self.assertRaisesRegex(ValueError, 'grid differs'):
            native.validate_readings(record, CAMERA, (3., 4., 5.), points, (100, 100))

    def side_fixture(self, folder):
        image = np.full((100, 100, 3), 130, dtype=np.uint8)
        path = folder / 'opaque.png'
        Image.fromarray(image).save(path)
        calibration = folder / 'calibration.json'
        calibration.write_text('{}', encoding='ascii')
        record = readings({key: grid['points'] for key, grid in native.grids().items()})
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        record.update(session_binding=BINDING, source_contract_sha256='source',
            capture_sha256=checksum, dry_capture_sha256='dry', capture_size=[100, 100])
        opaque = 'full_pool_wet_side_opaque'
        source = {'camera_calibration': {'path': str(calibration),
            'sha256': hashlib.sha256(calibration.read_bytes()).hexdigest()},
            'session_binding': BINDING, 'source_contract_sha256': 'source', 'frozen': True,
            'native_side_projection': {'schema': 1, 'coordinate_units': 'physical_pixels', 'rows': {opaque: record}},
            'captures': {opaque: {'path': str(path), 'sha256': checksum}, 'full_pool_dry': {'sha256': 'dry'}},
            'rows': {'full_pool_dry': {'camera_after': CAMERA}, 'full_pool_wet': {}},
            'extra_rows': {opaque: {'requested_alpha': 1., 'camera_after': CAMERA, 'ready': {'origin': [3., 4., 5.]}}}}
        images = {opaque: image, 'full_pool_wet': np.full_like(image, 100),
                  'full_pool_dry': np.full_like(image, 20), 'full_pool_wet_section': np.full_like(image, 20),
                  'full_pool_wet_section_restored': np.full_like(image, 100),
                  'full_pool_wet_side_default_restored': np.full_like(image, 100)}
        return source, opaque, images

    def test_session_source_frame_and_physical_viewport_are_all_bound(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(native, 'validate_calibration', return_value={}), \
                patch('analyze_product_water.expected_mask', return_value=np.ones((100, 100), dtype=bool)):
            source, label, images = self.side_fixture(Path(directory))
            self.assertEqual(8, len(native.side_coordinates(source, label, images)))
            for key, value in (('session_binding', dict(BINDING, id='other')),
                               ('source_contract_sha256', 'other'), ('capture_sha256', 'other'),
                               ('dry_capture_sha256', 'other'), ('capture_size', [25, 25])):
                with self.subTest(key=key):
                    changed = copy.deepcopy(source)
                    changed['native_side_projection']['rows'][label][key] = value
                    with self.assertRaises(ValueError):
                        native.side_coordinates(changed, label, images)

    def test_stale_wet_opaque_section_and_bad_restore_pixels_reject(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(native, 'validate_calibration', return_value={}), \
                patch('analyze_product_water.expected_mask', return_value=np.ones((100, 100), dtype=bool)):
            source, label, images = self.side_fixture(Path(directory))
            for changed_label, reference in (('full_pool_dry', 'full_pool_wet'),
                    ('full_pool_wet_section', 'full_pool_wet'),
                    ('full_pool_wet_section_restored', 'full_pool_dry'),
                    ('full_pool_wet_side_default_restored', 'full_pool_dry')):
                with self.subTest(label=changed_label):
                    changed = dict(images, **{changed_label: images[reference]})
                    with self.assertRaises(ValueError):
                        native.side_coordinates(source, label, changed)
            images[label][:] = images['full_pool_wet']
            with self.assertRaisesRegex(ValueError, 'opaque control is stale'):
                native.side_coordinates(source, label, images)

    def test_missing_native_contract_rejects_instead_of_falling_back_to_analytic(self):
        image = np.zeros((100, 100, 3), dtype=np.uint8)
        source = {'routes': ['full'], 'native_side_projection_requested': True,
            'opaque_side_controls_requested': True, 'rows': {'full_pool_wet': {'ready': {'shapes': []}}},
            'extra_rows': {'full_pool_wet_side_opaque': {'requested_alpha': 1.}}}
        images = {'full_pool_wet': image, 'full_pool_dry': image, 'full_pool_wet_side_opaque': image}
        measured = side_checks(source, images)
        self.assertEqual(2, len(measured))
        self.assertTrue(all(row['passed'] is False and row['oracle'] == 'native_api' for row in measured.values()))

    def test_native_calibration_requires_matching_session_and_source(self):
        calibration = {'native_projection': {'schema': 1, 'coordinate_units': 'physical_pixels',
            'session_binding': BINDING, 'source_contract_sha256': 'source'}}
        for binding, contract in ((dict(BINDING, id='other'), 'source'), (BINDING, 'other')):
            with self.assertRaisesRegex(ValueError, 'another session or source'):
                native.validate_calibration(calibration, binding, contract)


if __name__ == '__main__':
    unittest.main()
