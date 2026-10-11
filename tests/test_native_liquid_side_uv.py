"""Independent artwork fixtures test discrimination, never native acceptance."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from measure_native_liquid_side_uv import (
    DEFAULT_LIMITS, Hypothesis, fingerprint, hypotheses_from_plan, load_artwork,
    load_native_contract, measure, side_grid, spatial_templates, validate_control_cells,
)

TRUE = Hypothesis('nw', 'bottom', 'identity', 2, True, .25)


def independent_fixture():
    rng = np.random.default_rng(1729)
    gray = rng.integers(20, 236, (8, 32, 32))
    strip = np.repeat(gray[..., None], 3, axis=-1).astype(float)
    seconds = np.asarray([0., .019, .044, .068, .117, .151, .233, .319, .491, .629, .817])
    roles = ['calibration'] * 3 + ['training'] * 4 + ['holdout'] * 4
    columns = np.asarray([3, 5, 7, 9, 11, 13])
    sequences = []
    for name, top, rows, geometry_role in (
        ('deep_training', .9, [6, 8, 10, 12], 'training'),
        ('shallow_holdout', .55, [9, 10, 11, 12], 'holdout'),
    ):
        x, y = np.meshgrid(columns, rows)
        x, y = x.ravel(), y.ravel()
        # The expected quarter samples are direct integer array accesses. No
        # measured UV, orientation, bilinear, or clock helper creates this data.
        samples = strip[:, y, x]
        clock = seconds * 10 + .25
        first = np.floor(clock).astype(int) % len(strip)
        fraction = (clock - np.floor(clock))[:, None, None]
        texture = samples[first] * (1 - fraction) + samples[(first + 1) % len(strip)] * fraction
        background = rng.uniform(90, 170, texture.shape)
        positive = .65 * background + texture * np.asarray([.18, .41, .62]) + [2., -3., 5.]
        sequences.append({'id': name, 'geometry_role': geometry_role,
                          'grid': {'u': x / 15, 'height': 1 - y / 15,
                                   'top': np.full(len(x), top)},
                          'seconds': seconds.copy(), 'roles': roles[:],
                          'positive': positive, 'background': background})
    hypotheses = [Hypothesis(region, v, 'identity', ticks, True, phase)
                  for region in ('nw', 'full') for v in ('bottom', 'stretch')
                  for ticks in (1, 2, 3, 4) for phase in (0, .25, .5, .75)]
    return strip, sequences, hypotheses


def write_json(path, value):
    path.write_text(json.dumps(value), encoding='utf8')
    return fingerprint(path)


def artwork_fixture(directory):
    (directory / 'textures/blocks').mkdir(parents=True)
    png = directory / 'textures/blocks/water_flow_grey.png'
    Image.fromarray(np.full((64, 32, 4), 128, dtype=np.uint8), 'RGBA').save(png)
    blocks = write_json(directory / 'blocks.json', {'water': {'textures': {'side': 'flowing_water_grey'}}})
    atlas = write_json(directory / 'textures/terrain_texture.json', {
        'texture_data': {'flowing_water_grey': {'textures': 'textures/blocks/water_flow_grey', 'quad': 1}}})
    flipbook = write_json(directory / 'textures/flipbook_textures.json', [
        {'atlas_tile': 'flowing_water_grey', 'flipbook_texture': 'textures/blocks/water_flow_grey', 'replicate': 2}])
    return {'native_name': 'minecraft:water', 'blocks': blocks, 'atlas': atlas,
            'flipbook': flipbook, 'png': fingerprint(png)}


def control_plan():
    water = [[0, 0, 0], ['minecraft:water', 0]]
    stone = [[0, -1, 0], ['minecraft:stone', 0]]
    return {'reserved': [[0, 0, 0], [0, -1, 0], [5, -1, 5]], 'platform': [5, -1, 5],
            'controls': {'supported_positive': {'cells': [water, stone]},
                         'supported_negative': {'cells': [stone]},
                         'liquid_only': {'cells': [deepcopy(water)]}, 'empty': {'cells': []}}}


def native_contract_fixture(directory):
    session_path = directory / 'session.json'
    session = {'owner': 'synthetic_loader_test', 'id': 'synthetic_loader_test',
               'game_pid': 123, 'game_identity': '456', 'session_file': str(session_path)}
    write_json(session_path, session)
    camera = {'position': [-3., 2., -4.], 'target': [.5, .4, .5], 'screen': [200, 120],
              'native_image_screen': [200, 120], 'vertical_fov': 60.}
    pose = {'stable': {'screen': [200, 120], 'fov': 60.}}
    calibration = write_json(directory / 'calibration.json', {
        'completed': True, 'passed': True, 'restored': True, 'cleanup_errors': [],
        'vertical_fov': 60., 'session_file': str(session_path)})
    plan = control_plan()
    rng = np.random.default_rng(314)
    png_path = directory / 'capture.png'
    Image.fromarray(rng.integers(0, 256, (120, 200, 3), dtype=np.uint8), 'RGB').save(png_path)
    png_record = fingerprint(png_path)
    png_record.update(bytes=png_path.stat().st_size, size=[200, 120], background_only=True,
                      camera_before=pose['stable'], camera_after=pose['stable'])
    png_record['capture'] = dict(session, ok=True, reliable=True, background_only=True, background_safe=True,
                                 backend='Windows.Graphics.Capture', sha256=png_record['sha256'],
                                 bytes=png_record['bytes'], window={'pid': 123})
    def frame(control, stamp):
        cells = {tuple(pos): value for pos, value in plan['controls'][control]['cells']}
        cells[tuple(plan['platform'])] = ['minecraft:stone', 0]
        snapshot = {'valid': True, 'cells': [
            {'pos': pos, 'foreground': cells.get(tuple(pos), ['minecraft:air', 0]),
             'background': ['minecraft:air', 0], 'actor': False} for pos in plan['reserved']]}
        capture = deepcopy(png_record)
        capture['capture']['frame'] = {'ok': True, 'frame_qpc_100ns': stamp,
                                        'request_qpc_100ns': stamp - 1, 'width': 200, 'height': 120}
        return {'control': control, 'capture': capture,
                'native_before_capture': {'server': deepcopy(snapshot), 'client': deepcopy(snapshot)},
                'native_after_capture': {'server': deepcopy(snapshot), 'client': deepcopy(snapshot)}}
    frames = [frame('supported_positive', stamp) for stamp in (1000000, 2000000, 3000000)]
    for row, role in zip(frames, ('calibration', 'training', 'holdout')):
        row['role'] = role
    item = {'id': 'source0', 'geometry_role': 'training', 'case': 'source0', 'source_plan': plan,
            'temporal_control': 'supported_positive',
            'camera': camera, 'camera_pose': pose,
            'surfaces': [{'cell_origin': [0, 0, 0], 'corner_heights': [.8] * 4, 'side': 'north'}],
            'static_controls': {control: frame(control, 500000) for control in plan['controls']}, 'frames': frames}
    source_report = write_json(directory / 'source_report.json', {
        'session_file': str(session_path), 'cases': [{'case': 'source0', 'source': plan}]})
    source_artifact = write_json(directory / 'source_artifact.json', {'fixture': 'synthetic_loader_test'})
    shape = write_json(directory / 'shape.json', {
        'all_selected_silhouettes_passed': True, 'calibration': calibration, 'report': source_report,
        'analyzer': source_artifact, 'profile': source_artifact, 'sources': {'fixture': source_artifact},
        'rows': [{'case': 'source0', 'camera': camera, 'silhouette_passed': True,
                  'original_pixel_controls_passed': True,
                  'raw_captures': {control: fingerprint(png_path) for control in plan['controls']},
                  'surfaces': [{'position': [0, 0, 0], 'heights': [.8] * 4, 'faces': 2}]}]})
    contract = {'schema_version': 1, 'native_name': 'minecraft:water', 'completed': True, 'restored': True,
            'cleanup_errors': [], 'setter': 'SetBlockNew', 'flow_freeze': {'forbidden': True},
            'flow_restore': {'native_return_verified': True}, 'calibration': calibration,
            'shape_analysis': shape, 'session_binding': session, 'sample_grid': {'u': [.2, .4, .6, .8],
            'vertical_fraction': [.2, .4, .6, .8]}, 'clock_origin_qpc_100ns': 0, 'sequences': [item],
            'hypotheses': {'test_only': True}}
    declared = {key: item[key] for key in ('id', 'case', 'geometry_role', 'surfaces', 'source_plan', 'camera',
                                         'camera_pose', 'temporal_control')}
    declared['frame_roles'] = [row['role'] for row in frames]
    contract['preflight'] = write_json(directory / 'preflight.json', {
        'created_qpc_100ns': 100, 'session_binding': session, 'sample_grid': contract['sample_grid'],
        'hypotheses': contract['hypotheses'], 'sequences': [declared]})
    return contract


class SideArtworkDiscriminationTests(unittest.TestCase):
    def setUp(self):
        self.strip, self.sequences, self.hypotheses = independent_fixture()

    def test_correct_mapping_cadence_and_independent_geometry_pass(self):
        result = measure(self.strip, self.sequences, self.hypotheses)
        self.assertTrue(result['passed'])
        self.assertEqual(TRUE.__dict__, result['selected'])
        self.assertLess(result['holdout_rgb_rmse'], 1e-7)
        self.assertTrue(all(row['identified'] for row in result['identification'].values()))
        self.assertFalse(result['native_uv_accepted'])
        self.assertFalse(result['native_geometry_accepted'])
        self.assertFalse(result['production_accepted'])

    def test_wrong_stretched_v_full_sampling_and_cadence_fail(self):
        for field, value in (('side_v', 'stretch'), ('region', 'full'), ('ticks_per_frame', 4)):
            wrong = dict(TRUE.__dict__, **{field: value})
            with self.subTest(field=field):
                result = measure(self.strip, self.sequences, [Hypothesis(**wrong)], required_properties=())
                self.assertFalse(result['passed'])
                self.assertGreater(result['holdout_rgb_rmse'], DEFAULT_LIMITS['maximum_rgb_rmse'])

    def test_holdout_pixels_cannot_change_training_selection(self):
        first = measure(self.strip, self.sequences, self.hypotheses)
        for sequence in self.sequences:
            if sequence['geometry_role'] == 'holdout':
                sequence['positive'][:] = 0
            else:
                sequence['positive'][np.asarray(sequence['roles']) == 'holdout'] = 0
        changed = measure(self.strip, self.sequences, self.hypotheses)
        self.assertEqual(first['selected'], changed['selected'])
        self.assertEqual(first['training_rgb_rmse'], changed['training_rgb_rmse'])
        self.assertFalse(changed['passed'])

    def test_constant_visible_color_fails_signal_and_null_gates(self):
        for sequence in self.sequences:
            sequence['positive'][:] = [80., 120., 180.]
        result = measure(self.strip, self.sequences, self.hypotheses)
        self.assertFalse(result['passed'])
        self.assertTrue(all(row['texture_rms'] < 2 for row in result['holdouts'].values()))

    def test_declared_wrong_property_controls_are_required(self):
        result = measure(self.strip, self.sequences, [TRUE])
        self.assertFalse(result['passed'])
        self.assertTrue(all(row['reason'] == 'no_declared_wrong_property_control'
                            for row in result['identification'].values()))

    def test_wrong_clock_control_is_found_in_every_spatial_group(self):
        candidates = [Hypothesis(region, 'bottom', 'identity', ticks, True, .25)
                      for region in ('nw', 'full') for ticks in (1, 2)]
        scores = {('nw', 2): 0., ('nw', 1): 1., ('full', 2): .1, ('full', 1): .2}
        def evaluate(unused_strip, unused_sequences, batch, include_holdouts=False):
            errors = np.asarray([scores[(item.region, item.ticks_per_frame)] for item in batch])
            if include_holdouts:
                errors = np.asarray([0. if item.region == 'nw' and item.ticks_per_frame == 2 else 10.
                                     for item in batch])
            metrics = {'sequence': {'rgb_rmse': errors, 'explained_variance': np.ones(len(batch)),
                'texture_rms': np.full(len(batch), 20.), 'photometric': {'opacity': np.ones(len(batch))},
                'points': 24, 'frames': 4}}
            return errors, metrics
        with patch('measure_native_liquid_side_uv.evaluate_batch', side_effect=evaluate):
            result = measure(self.strip, self.sequences, candidates, required_properties=('ticks_per_frame',))
        clock = result['identification']['ticks_per_frame']
        self.assertEqual('full', clock['alternative']['region'])
        self.assertEqual(.2, clock['training_margin_rgb_rmse'])
        self.assertFalse(clock['identified'])

    def test_training_geometry_and_temporal_roles_are_required(self):
        for mutation in ('geometry', 'holdout_frames', 'training_frames', 'duplicate_time', 'reverse_time'):
            data = deepcopy(self.sequences)
            if mutation == 'geometry':
                data[1]['geometry_role'] = 'training'
            elif mutation.endswith('_frames'):
                role = mutation.removesuffix('_frames')
                data[0]['roles'] = ['calibration' if item == role else item for item in data[0]['roles']]
            elif mutation == 'duplicate_time':
                data[0]['seconds'][1] = data[0]['seconds'][0]
            else:
                data[0]['seconds'] = data[0]['seconds'][::-1]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                measure(self.strip, data, self.hypotheses)

    def test_nonfinite_grid_and_threshold_relaxation_are_rejected(self):
        for key, value in (('maximum_rgb_rmse', 3.1), ('minimum_explained_variance', .89),
                           ('minimum_texture_rms', 1.9), ('minimum_property_margin_rmse', .49)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                measure(self.strip, self.sequences, self.hypotheses, limits={key: value})
        self.sequences[0]['grid']['height'][0] = np.nan
        with self.assertRaises(ValueError):
            measure(self.strip, self.sequences, self.hypotheses)

    def test_side_face_corner_interpolation_is_world_derived(self):
        corners = [.2, .4, .6, .8]
        expected = {'north': ([10.25, 20.125, 30.], .25),
                    'south': ([10.75, 20.325, 31.], .65),
                    'west': ([10., 20.325, 30.75], .65),
                    'east': ([11., 20.225, 30.25], .45)}
        for side, (point, top) in expected.items():
            with self.subTest(side=side):
                grid = side_grid([10, 20, 30], corners, side, [.25], [.5])
                np.testing.assert_allclose([point], grid['world_points'])
                np.testing.assert_allclose([top], grid['top'])
        with self.assertRaises(ValueError):
            side_grid([0, 0, 0], corners, 'north', [0], [.5])

    def test_top_bottom_vertical_flip_equivalence_is_explicit(self):
        grid = self.sequences[0]['grid']
        bottom = spatial_templates(self.strip, grid, TRUE)
        top = spatial_templates(self.strip, grid, Hypothesis('nw', 'top', 'flip_y', 2, True, .25))
        np.testing.assert_allclose(bottom, top)
        result = measure(self.strip, self.sequences, self.hypotheses)
        self.assertIn('equivalent', result['orientation_identification_scope'])

    def test_phase_grid_and_every_replication_offset_are_explicit(self):
        plan = {'regions': ['full', 'nw', 'ne', 'sw', 'se'], 'side_v': ['bottom', 'top', 'stretch'],
                'orientations': ['identity', 'rot90'], 'ticks_per_frame': [1, 2],
                'blend_frames': [False, True], 'pixel_mapping': ['centers', 'edges'], 'phase_steps_per_frame': 2}
        hypotheses = hypotheses_from_plan(plan, 8)
        self.assertEqual(5 * 3 * 2 * 2 * 2 * 2 * 16, len(hypotheses))
        self.assertEqual(7.5, max(item.phase for item in hypotheses))
        plan['phase_steps_per_frame'] = 17
        with self.assertRaises(ValueError):
            hypotheses_from_plan(plan, 8)


class EvidenceBindingTests(unittest.TestCase):
    def test_artwork_uses_original_bitmap_metadata_and_rejects_alias_or_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = artwork_fixture(directory)
            strip, metadata = load_artwork(source)
            self.assertEqual((2, 32, 32, 3), strip.shape)
            self.assertEqual(2, metadata['flipbook']['replicate'])
            self.assertFalse(metadata['ticks_per_frame_explicit'])
            for mutation in ('alias', 'hash', 'path'):
                changed = deepcopy(source)
                if mutation == 'alias':
                    changed['native_name'] = 'minecraft:flowing_water'
                elif mutation == 'hash':
                    changed['png']['sha256'] = '0' * 64
                else:
                    duplicate = directory / 'copy.png'
                    duplicate.write_bytes(Path(source['png']['path']).read_bytes())
                    changed['png'] = fingerprint(duplicate)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    load_artwork(changed)

    def test_both_source_control_pairs_bind_the_exact_same_water(self):
        plan = control_plan()
        self.assertEqual({(0, 0, 0)}, validate_control_cells(plan))
        for mutation in ('alias', 'layered', 'duplicate', 'other_depth', 'context'):
            changed = deepcopy(plan)
            if mutation == 'alias':
                changed['controls']['liquid_only']['cells'][0][1][0] = 'minecraft:flowing_water'
            elif mutation == 'layered':
                changed['controls']['supported_positive']['cells'][0][1] = {'foreground': ['minecraft:water', 0]}
            elif mutation == 'duplicate':
                changed['controls']['supported_positive']['cells'].append(changed['controls']['supported_positive']['cells'][0])
            elif mutation == 'other_depth':
                changed['controls']['liquid_only']['cells'][0][1][1] = 3
            else:
                changed['controls']['empty']['cells'] = [[[0, -1, 0], ['minecraft:quartz_block', 0]]]
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_control_cells(changed)

    def test_native_loader_checks_capture_camera_source_and_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            contract = native_contract_fixture(Path(temporary))
            result = load_native_contract(contract)
            self.assertEqual(1, len(result))
            self.assertEqual((3, 16, 3), result[0]['positive'].shape)
            np.testing.assert_allclose([.1, .2, .3], result[0]['seconds'])
            for mutation in ('owner', 'stale', 'camera', 'state', 'surface', 'empty_surfaces', 'restore',
                             'preflight_time', 'preflight_roles', 'preflight_grid', 'preflight_control'):
                changed = deepcopy(contract)
                frame = changed['sequences'][0]['frames'][0]
                if mutation == 'owner':
                    frame['capture']['capture']['owner'] = 'other_owner'
                elif mutation == 'stale':
                    frame['capture']['capture']['frame']['request_qpc_100ns'] += 2
                elif mutation == 'camera':
                    frame['capture']['camera_after']['fov'] = 61.
                elif mutation == 'state':
                    frame['native_after_capture']['client']['cells'][0]['foreground'][1] = 3
                elif mutation == 'surface':
                    changed['sequences'][0]['surfaces'][0]['corner_heights'][0] = .7
                elif mutation == 'empty_surfaces':
                    changed['sequences'][0]['surfaces'] = []
                elif mutation == 'preflight_time':
                    frame['capture']['capture']['frame']['frame_qpc_100ns'] = 99
                    frame['capture']['capture']['frame']['request_qpc_100ns'] = 98
                elif mutation == 'preflight_roles':
                    frame['role'] = 'holdout'
                elif mutation == 'preflight_grid':
                    changed['sample_grid']['u'][0] = .3
                elif mutation == 'preflight_control':
                    changed['sequences'][0]['temporal_control'] = 'liquid_only'
                else:
                    changed['restored'] = False
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    load_native_contract(changed)


if __name__ == '__main__':
    unittest.main()
