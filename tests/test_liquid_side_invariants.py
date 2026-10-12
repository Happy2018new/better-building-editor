"""Independent physical image fixtures discriminate defects, never native facts."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
import analyze_liquid_sides as sides


def marker_bitmap():
    # Unequal run lengths and non-palindromic lower rows keep low crop observable.
    columns = np.arange(64)[None, :]
    rows = np.arange(64)[:, None]
    horizontal = ((columns >= 3) & (columns < 9)) | ((columns >= 16) & (columns < 29))
    vertical = ((rows >= 5) & (rows < 14)) | ((rows >= 22) & (rows < 31))
    vertical |= ((rows >= 41) & (rows < 48)) | ((rows >= 55) & (rows < 59))
    bits = horizontal ^ vertical
    return np.repeat(np.where(bits, 224, 32)[..., None], 3, axis=2).astype(float)


def declaration(source=sides.SOURCE_IDS[0], face='north', scale=500., position=(3, 3, 3)):
    x, y, z = position
    offset, floor = 30., 580.
    # These coefficients are written from four physical face definitions, not
    # from face_points(), project(), side_grid(), or marker_expected().
    first = {'north': [scale, 0, 0, offset-scale*x],
             'south': [-scale, 0, 0, offset+scale*(x+1)],
             'west': [0, 0, -scale, offset+scale*(z+1)],
             'east': [0, 0, scale, offset-scale*z]}[face]
    projection = {'kind': 'affine', 'screen': [580, 620], 'native_image_screen': [580, 620],
                  'origin': [0, 0, 0], 'affine': [first, [0, -scale, 0, floor+scale*y]],
                  'toward': list(sides.NORMALS[face])}
    side = {'position': list(position), 'layer': 0, 'face': face}
    return {'id': source+'/'+face, 'route': 'scene', 'role': 'marker', 'view': 'vnw',
            'source_id': source, 'control': 'supported_positive', 'projection': projection,
            'source_cells': sides.builtin_geometry(source)['source_cells'], 'sides': [side]}


def physical_image(row, mapping='bottom', left=None, right=None):
    """Independent pixel-array raster: image X is U, image Y is physical height."""
    marker = marker_bitmap()
    source = row['source_id']
    if left is None:
        left = 178/255. if source == sides.SOURCE_IDS[0] else 35/255.
    if right is None:
        right = left
    scale = abs(max(row['projection']['affine'][0][:3], key=abs))
    px, py = np.meshgrid(np.arange(580), np.arange(620))
    u, height = (px-30.)/scale, (580.-py)/scale
    top = left*(1-u)+right*u
    v = (1-height if mapping == 'bottom' else 1-height/top if mapping == 'stretch'
         else height if mapping == 'reverse_v' else 1-height)
    tx = np.floor((1-u if mapping == 'reverse_u' else u)*32).astype(int)
    ty = np.floor(v*32).astype(int)
    image = np.full((620, 580, 3), 80., float)
    visible = (u >= 0) & (u <= 1) & (height >= 0) & (height <= top)
    image[visible] = marker[np.clip(ty[visible], 0, 63), np.clip(tx[visible], 0, 63)]
    return image


def observed_state(source=sides.SOURCE_IDS[2]):
    geometry = sides.builtin_geometry(source)
    rows = []
    for surface in geometry['surfaces']:
        faces = surface['faces']
        for mask, texture, template in ((faces & 1, 'still_water_grey', None),
                                         (faces & 30, 'flowing_water_grey', 'test_bottom'),
                                         (faces & 32, 'still_water_grey', None)):
            if mask:
                rows.append(dict(surface, faces=mask, texture=texture, template=template,
                                 rotation=0, tint=[63, 118, 228]))
    return {'ready': True, 'occupancy_settled': True, 'source_cells': geometry['source_cells'],
            'quantized_surfaces': rows}


def replay_fixture(directory):
    positive = declaration()
    positive['id'] = 'positive'
    positive['background_id'] = 'negative'
    negative = dict(deepcopy(positive), id='negative', control='supported_negative', sides=[])
    negative.pop('background_id')
    negative['source_cells'] = sides.builtin_geometry(negative['source_id'], 'supported_negative')['source_cells']
    plan = {'schema': 1, 'kind': 'liquid_side_visible_v1', 'limits': sides.LIMITS,
            'source_bindings': sides.source_bindings(), 'declarations': [positive, negative]}
    marker_path = directory/'marker.png'
    rgba = np.concatenate((marker_bitmap().astype(np.uint8), np.full((64, 64, 1), 255, np.uint8)), axis=2)
    Image.fromarray(rgba).save(marker_path)
    plan['marker'] = sides.fingerprint(marker_path)
    plan_path = directory/'plan.json'
    plan_path.write_text(json.dumps(plan), encoding='ascii')
    receipt_path = directory/'preflight.json'
    receipt_path.write_text(json.dumps({'plan_sha256': sides.fingerprint(plan_path)['sha256'],
        'geometry': sides.validate_plan(plan), 'created_qpc_100ns': 100}), encoding='ascii')
    binding = {'id': 'synthetic_offline_only', 'owner': 'synthetic_offline_only', 'game_pid': 1,
               'game_identity': 'synthetic_offline_only', 'session_file': str(directory/'session.json')}
    captures, states = {}, {}
    for row, image in ((positive, physical_image(positive)), (negative, np.full((620, 580, 3), 80.))):
        path = directory/(row['id']+'.png')
        Image.fromarray(image.astype(np.uint8)).save(path)
        captures[row['id']] = dict(sides.fingerprint(path), **binding, width=580, height=620,
            variance=[1000., 1000., 1000.], backend='Windows.Graphics.Capture',
            frame={'backend': 'Windows.Graphics.Capture', 'frame_qpc_100ns': 200, 'request_qpc_100ns': 190},
            ok=True, reliable=True, background_only=True, background_safe=True, native_resolution=True)
        state = observed_state(sides.SOURCE_IDS[0])
        if row['id'] == 'negative':
            state['quantized_surfaces'] = []
        state.update(source_cells=row['source_cells'], projection_before=row['projection'], projection_after=row['projection'])
        states[row['id']] = state
    evidence = {'schema': 1, 'evidence_kind': 'synthetic_fixture', 'plan': sides.fingerprint(plan_path),
                'preflight': sides.fingerprint(receipt_path), 'session_binding': binding,
                'completed': True, 'restored': True, 'cleanup_errors': [], 'captures': captures, 'states': states}
    evidence_path = directory/'evidence.json'
    evidence_path.write_text(json.dumps(evidence), encoding='ascii')
    return plan_path, evidence_path, evidence


def original_replay_fixture(directory):
    plan_path, evidence_path, evidence = replay_fixture(directory)
    plan = json.loads(plan_path.read_bytes())
    candidate = plan['declarations'][0]
    candidate['role'] = 'original'
    native = dict(deepcopy(candidate), id='native', route='native', role='native_original')
    native.pop('background_id')
    plan['declarations'].append(native)
    plan['original_pairs'] = [{'id': 'original', 'candidate': 'positive', 'native': 'native'}]
    plan['original_artwork'] = {
        'still': {'path': str(directory/'stub-original-still.png'),
                  'sha256': 'db3edc3132d88a595d466e90840a8e8839593776421435c23aa880fbd2a779c3'},
        'flow': {'path': str(directory/'stub-original-flow.png'),
                 'sha256': 'f803fa03de42513b8e19db50e8c0743c5c82a06337afe0191efddd3e47684246'}}
    plan_path.write_text(json.dumps(plan), encoding='ascii')
    evidence['plan'] = sides.fingerprint(plan_path)
    receipt_path = directory/'preflight.json'
    receipt_path.write_text(json.dumps({'plan_sha256': evidence['plan']['sha256'],
        'geometry': sides.validate_plan(plan), 'created_qpc_100ns': 100}), encoding='ascii')
    evidence['preflight'] = sides.fingerprint(receipt_path)
    evidence['evidence_kind'] = 'physical_native_capture'
    evidence['states']['positive'].pop('quantized_surfaces')
    evidence['states']['positive']['groups'] = [{'origin': [0, 0, 0], 'layer': 0,
        'uniforms': [[2047, 0, 0, 0], [45746, 45746, 0, 0], [0, 0, 0, 0], [39686, .45, 4159204, 1]],
        'texture': 'still_water_grey', 'template': None, 'visible': True}]
    evidence['states']['negative']['groups'] = []
    evidence['captures']['native'] = deepcopy(evidence['captures']['positive'])
    readback_path = directory/'native-readback.json'
    cells = sides.builtin_geometry(native['source_id'])['native_readback_cells']
    readback_path.write_text(json.dumps({'session_binding': evidence['session_binding'],
        'before': cells, 'after': cells, 'flow_frozen': True,
        'original_artwork': plan['original_artwork']}), encoding='ascii')
    evidence['states']['native'] = {'projection_before': deepcopy(native['projection']),
        'projection_after': deepcopy(native['projection']), 'native_readbacks': sides.fingerprint(readback_path)}
    review_path = directory/'original-review.json'
    row = {key: 'OBSERVED' for key in ('four_face_direction', 'physical_height_crop',
                                      'original_side_artwork', 'original_top_artwork')}
    row['capture_sha256'] = {key: evidence['captures'][identity]['sha256']
                            for key, identity in (('candidate', 'positive'), ('native', 'native'))}
    review_path.write_text(json.dumps({'plan_sha256': evidence['plan']['sha256'],
        'reviewer': 'offline_fixture', 'pairs': {'original': row}}), encoding='ascii')
    evidence['original_review'] = sides.fingerprint(review_path)
    evidence_path.write_text(json.dumps(evidence), encoding='ascii')
    return plan_path, evidence_path, evidence, plan


class GeometryTests(unittest.TestCase):
    def test_known_independent_corner_and_hidden_face_tables(self):
        self.assertEqual(sides.builtin_geometry(sides.SOURCE_IDS[0])['surfaces'][0]['heights'], [178]*4)
        self.assertEqual(sides.builtin_geometry(sides.SOURCE_IDS[1])['surfaces'][0]['heights'], [35]*4)
        corner = sides.builtin_geometry(sides.SOURCE_IDS[2])
        self.assertEqual(sides.surface_at(corner, (3, 3, 3))['heights'], [222, 92, 43, 188])
        self.assertEqual(sides.surface_at(corner, (3, 3, 3))['faces'], 5)
        falling = sides.builtin_geometry(sides.SOURCE_IDS[3])['surfaces']
        self.assertEqual([(row['heights'], row['faces']) for row in falling],
                         [([255]*4, 30), ([255]*4, 30), ([178]*4, 31)])

    def test_geometry_does_not_call_runtime_shape_provider(self):
        with patch('projection.liquid_shape.DocumentLiquidShapes.surface', side_effect=AssertionError('runtime helper')):
            self.assertEqual(sides.builtin_geometry(sides.SOURCE_IDS[1])['surfaces'][0]['heights'], [35]*4)

    def test_semantic_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            sides.builtin_geometry('water_depth_7_foreground')

    def test_central_slope_hidden_face_cannot_satisfy_gate(self):
        row = declaration(sides.SOURCE_IDS[2])
        with self.assertRaisesRegex(ValueError, 'hidden'):
            sides.side_preflight(row, row['sides'][0], sides.builtin_geometry(row['source_id']))

    def test_low_side_resolution_and_camera_visibility_are_pre_capture(self):
        row = declaration(sides.SOURCE_IDS[1], scale=100)
        result = sides.side_preflight(row, row['sides'][0], sides.builtin_geometry(row['source_id']))
        self.assertFalse(result['adequate'])
        self.assertLess(result['minimum_side_pixels'], 24)
        row['projection']['toward'] = [0, 0, 1]
        with self.assertRaisesRegex(ValueError, 'away'):
            sides.side_preflight(row, row['sides'][0], sides.builtin_geometry(row['source_id']))

    def test_full_viewport_scaling_not_crop_or_fit(self):
        row = declaration()
        point = [[3.25, 3.1, 3.]]
        first = sides.project(point, row['projection'])
        row['projection']['native_image_screen'] = [1160, 1240]
        np.testing.assert_allclose(sides.project(point, row['projection']), first*2)


class SpatialImageTests(unittest.TestCase):
    def test_four_face_direction_from_independent_physical_pixels(self):
        for face in ('north', 'south', 'west', 'east'):
            with self.subTest(face=face):
                row = declaration(face=face)
                result = sides.marker_side(physical_image(row), row, row['sides'][0],
                                           sides.builtin_geometry(row['source_id']), marker_bitmap())
                self.assertEqual(result['status'], 'OBSERVED', result)
                self.assertGreaterEqual(result['marker_mask_iou'], .95)

    def test_reverse_u_v_and_stretched_texture_rejected(self):
        for mapping in ('reverse_u', 'reverse_v', 'stretch'):
            row = declaration()
            result = sides.marker_side(physical_image(row, mapping), row, row['sides'][0],
                                       sides.builtin_geometry(row['source_id']), marker_bitmap())
            self.assertEqual(result['status'], 'FAIL', (mapping, result))

    def test_flat_fill_never_passes_as_original_or_marker(self):
        row = declaration()
        result = sides.marker_side(np.full((620, 580, 3), 100.), row, row['sides'][0],
                                   sides.builtin_geometry(row['source_id']), marker_bitmap())
        self.assertEqual(result['status'], 'NOT_TESTED')

    def test_equal_height_crop_correct_and_stretched_defect(self):
        high, low = declaration(), declaration(sides.SOURCE_IDS[1])
        correct = sides.crop_registration(physical_image(high), physical_image(low), high, low,
                                         high['sides'][0], low['sides'][0], marker_bitmap())
        self.assertEqual(correct['status'], 'OBSERVED', correct)
        self.assertEqual(correct['landmark_boundary_euclidean_capped_pixels'], 0.)
        wrong = sides.crop_registration(physical_image(high, 'stretch'), physical_image(low, 'stretch'),
                                       high, low, high['sides'][0], low['sides'][0], marker_bitmap())
        self.assertEqual(wrong['status'], 'FAIL', wrong)

    def test_low_resolution_stays_not_tested(self):
        high, low = declaration(), declaration(sides.SOURCE_IDS[1], scale=100)
        result = sides.crop_registration(physical_image(high), physical_image(low), high, low,
                                        high['sides'][0], low['sides'][0], marker_bitmap())
        self.assertEqual(result['status'], 'NOT_TESTED')

    def test_full_cube_shader_defect_is_visible_even_with_correct_state(self):
        row = declaration()
        geometry = sides.builtin_geometry(row['source_id'])
        # A frontal camera does not see a top. Pixel fixture is a direct rectangle.
        correct = sides.silhouette(physical_image(row), np.full((620, 580, 3), 80.), row, geometry)
        self.assertEqual(correct['status'], 'OBSERVED', correct)
        full = sides.silhouette(physical_image(row, left=1.), np.full((620, 580, 3), 80.), row, geometry)
        self.assertEqual(full['status'], 'FAIL')

    def test_slope_left_right_swaps_change_physical_boundary(self):
        row = declaration(sides.SOURCE_IDS[2], face='north', position=(3, 3, 2))
        geometry = sides.builtin_geometry(row['source_id'])
        # Compare this one exposed slope against a direct linear-height raster.
        surface = sides.surface_at(geometry, (3, 3, 2))
        geometry['surfaces'] = [surface]
        left, right = 192/255., 50/255.
        correct = sides.silhouette(physical_image(row, left=left, right=right),
                                   np.full((620, 580, 3), 80.), row, geometry)
        self.assertEqual(correct['status'], 'OBSERVED', correct)
        wrong = sides.silhouette(physical_image(row, left=right, right=left),
                                 np.full((620, 580, 3), 80.), row, geometry)
        self.assertEqual(wrong['status'], 'FAIL')


class MissingAndContractTests(unittest.TestCase):
    def test_literal_applied_owner_payload_decodes_without_runtime_helper(self):
        group = {'origin': [0, 0, 0], 'uniforms': [[2047, 0, 0, 0], [45746, 45746, 0, 0],
                  [0, 0, 0, 0], [39686, .45, 4159204, 1]], 'layer': 0,
                 'texture': 'still_water_grey', 'template': None, 'visible': True}
        rows = sides.decode_groups([group])
        self.assertEqual(rows[0]['position'], [3, 3, 3])
        self.assertEqual(rows[0]['heights'], [178]*4)
        self.assertEqual(rows[0]['faces'], 31)
        self.assertEqual(rows[0]['tint'], [63, 118, 228])
        state = {'groups': [group], 'quantized_surfaces': deepcopy(rows)}
        state['quantized_surfaces'][0]['heights'][0] -= 1
        with self.assertRaisesRegex(ValueError, 'disagree'):
            sides.state_surfaces(state)

    def test_geometry_catches_flat_slope_and_exposed_falling_internal_face(self):
        state = observed_state()
        position = state['quantized_surfaces'][0]['position']
        for row in state['quantized_surfaces']:
            if row['position'] == position:
                row['heights'] = [178]*4
        self.assertEqual(sides.geometry_state(state, sides.builtin_geometry(sides.SOURCE_IDS[2]))['status'], 'FAIL')
        state = observed_state(sides.SOURCE_IDS[3])
        state['quantized_surfaces'][0]['faces'] |= 1
        self.assertEqual(sides.geometry_state(state, sides.builtin_geometry(sides.SOURCE_IDS[3]))['status'], 'FAIL')

    def test_missing_source_neighbor_does_not_change_survivor_corners_or_faces(self):
        before = observed_state()
        occupied = deepcopy(before)
        occupied['quantized_surfaces'] = [row for row in occupied['quantized_surfaces'] if row['position'] != [2, 3, 3]]
        occupied['quantized_surfaces'].reverse()
        self.assertEqual(sides.missing_invariant(before, occupied, deepcopy(before), [[2, 3, 3]])['status'], 'OBSERVED')
        occupied['quantized_surfaces'][0]['heights'][0] -= 1
        self.assertEqual(sides.missing_invariant(before, occupied, deepcopy(before), [[2, 3, 3]])['status'], 'FAIL')

    def test_source_mutation_restore_drift_and_unsettled_occupancy_fail(self):
        before = observed_state()
        hidden = deepcopy(before)
        hidden['quantized_surfaces'] = [row for row in hidden['quantized_surfaces'] if row['position'] != [2, 3, 3]]
        changed = deepcopy(hidden)
        changed['source_cells'].pop()
        self.assertEqual(sides.missing_invariant(before, changed, before, [[2, 3, 3]])['status'], 'FAIL')
        restored = deepcopy(before)
        restored['quantized_surfaces'].pop()
        self.assertEqual(sides.missing_invariant(before, hidden, restored, [[2, 3, 3]])['status'], 'FAIL')
        hidden['occupancy_settled'] = False
        self.assertEqual(sides.missing_invariant(before, hidden, before, [[2, 3, 3]])['status'], 'NOT_TESTED')

    def test_duplicate_transport_faces_rejected(self):
        state = observed_state()
        state['quantized_surfaces'].append(deepcopy(state['quantized_surfaces'][0]))
        with self.assertRaisesRegex(ValueError, 'repeats'):
            sides.normalized_surfaces(state['quantized_surfaces'])

    def test_marker_original_frame_and_alpha_must_be_physical_bound(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'marker.png'
            marker = marker_bitmap().astype(np.uint8)
            rgba = np.concatenate((marker, np.full((64, 64, 1), 255, np.uint8)), axis=2)
            Image.fromarray(np.tile(rgba, (2, 1, 1))).save(path)
            np.testing.assert_equal(sides.marker_frame(sides.fingerprint(path)), marker)
            rgba[0, 0, 3] = 254
            Image.fromarray(rgba).save(path)
            with self.assertRaisesRegex(ValueError, 'opaque'):
                sides.marker_frame(sides.fingerprint(path))

    def test_threshold_relaxation_source_drift_and_incomplete_coverage(self):
        row = declaration()
        plan = {'schema': 1, 'kind': 'liquid_side_visible_v1', 'limits': dict(sides.LIMITS),
                'source_bindings': sides.source_bindings(), 'declarations': [row]}
        sides.validate_plan(plan)
        self.assertFalse(all(sides.coverage(plan).values()))
        plan['limits']['maximum_rgb_rmse'] = 4
        with self.assertRaisesRegex(ValueError, 'fixed'):
            sides.validate_plan(plan)
        plan['limits'] = dict(sides.LIMITS)
        plan['declarations'][0]['source_cells'] = []
        with self.assertRaisesRegex(ValueError, 'exact source'):
            sides.validate_plan(plan)

    def test_pair_ids_cannot_overwrite_results_in_any_collection(self):
        high, low = declaration(), declaration(sides.SOURCE_IDS[1])
        missing = [dict(deepcopy(declaration(sides.SOURCE_IDS[2], position=(3, 3, 2))),
                        id=identity, route='missing') for identity in ('baseline', 'occupied', 'restored')]
        missing[1]['occupied_positions'] = [[2, 3, 3]]
        original = dict(deepcopy(high), id='original_candidate', role='original')
        native = dict(deepcopy(high), id='native', route='native', role='native_original')
        pairs = {
            'crop_pairs': {'id': 'crop', 'high': high['id'], 'low': low['id'],
                           'high_side': high['sides'][0], 'low_side': low['sides'][0]},
            'missing_pairs': {'id': 'missing', 'baseline': 'baseline', 'occupied': 'occupied',
                              'restored': 'restored', 'occupied_positions': [[2, 3, 3]]},
            'original_pairs': {'id': 'original', 'candidate': 'original_candidate', 'native': 'native'}}
        plan = {'schema': 1, 'kind': 'liquid_side_visible_v1', 'limits': dict(sides.LIMITS),
                'source_bindings': sides.source_bindings(), 'declarations': [high, low]+missing+[original, native]}
        for collection, pair in pairs.items():
            sides.validate_plan(dict(plan, **{collection: [pair]}))
            with self.subTest(collection=collection, defect='duplicate'):
                changed = dict(plan, **{collection: [pair, deepcopy(pair)]})
                with self.assertRaisesRegex(ValueError, collection + ' require unique nonempty'):
                    sides.validate_plan(changed)
            for identity in ('', ' ', None, 1):
                with self.subTest(collection=collection, defect=identity):
                    changed = dict(plan, **{collection: [dict(pair, id=identity)]})
                    with self.assertRaisesRegex(ValueError, collection + ' require unique nonempty'):
                        sides.validate_plan(changed)

    def test_missing_actual_native_art_reference_is_not_tested(self):
        result = sides.original_review({}, {}, {})
        self.assertEqual(result['status'], 'NOT_TESTED')

    def test_captureless_replay_never_invents_native_success(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            plan = {'schema': 1, 'kind': 'liquid_side_visible_v1', 'limits': sides.LIMITS,
                    'source_bindings': sides.source_bindings(), 'declarations': [declaration()]}
            plan_path = directory/'plan.json'
            plan_path.write_text(json.dumps(plan), encoding='ascii')
            receipt_path = directory/'preflight.json'
            receipt_path.write_text(json.dumps({'plan_sha256': sides.fingerprint(plan_path)['sha256'],
                'geometry': sides.validate_plan(plan), 'created_qpc_100ns': 100}), encoding='ascii')
            evidence = {'schema': 1, 'plan': sides.fingerprint(plan_path), 'preflight': sides.fingerprint(receipt_path),
                        'session_binding': {}, 'captures': {}, 'completed': False, 'restored': False,
                        'cleanup_errors': [], 'evidence_kind': 'synthetic_fixture'}
            evidence_path = directory/'evidence.json'
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            result = sides.analyze(plan_path, evidence_path)
            self.assertTrue(result['capture_failures'])
            for flag in ('visible_side_correctness_observed', 'native_uv_accepted', 'native_animation_accepted',
                         'native_source_color_transfer_accepted', 'production_accepted'):
                self.assertFalse(result[flag])

    def test_complete_synthetic_structure_still_cannot_accept_native_or_original_art(self):
        with tempfile.TemporaryDirectory() as folder:
            plan, evidence_path, evidence = replay_fixture(Path(folder))
            result = sides.analyze(plan, evidence_path)
            self.assertEqual(result['capture_failures'], [])
            self.assertEqual(result['structural_status'], 'OBSERVED', result)
            self.assertEqual(result['original_art']['status'], 'NOT_TESTED')
            self.assertFalse(result['visible_side_correctness_observed'])
            self.assertFalse(result['native_source_color_transfer_accepted'])
            self.assertFalse(result['production_accepted'])

    def test_capture_predating_frozen_preflight_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            plan, evidence_path, evidence = replay_fixture(Path(folder))
            evidence['captures']['positive']['frame'].update(frame_qpc_100ns=100, request_qpc_100ns=90)
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            result = sides.analyze(plan, evidence_path)
            self.assertTrue(any('predates' in str(row) for row in result['capture_failures']))
            self.assertFalse(result['visible_side_correctness_observed'])

    def test_projection_and_viewport_drift_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            plan, evidence_path, evidence = replay_fixture(Path(folder))
            evidence['states']['positive']['projection_after'] = dict(evidence['states']['positive']['projection_after'],
                                                                       screen=[579, 620])
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            result = sides.analyze(plan, evidence_path)
            self.assertEqual(result['geometry']['positive']['status'], 'FAIL')
            self.assertFalse(result['visible_side_correctness_observed'])

    def test_native_projection_drift_invalidates_bound_original_review_and_acceptance(self):
        with tempfile.TemporaryDirectory() as folder:
            plan_path, evidence_path, evidence, plan = original_replay_fixture(Path(folder))
            original_read_reference = sides.read_reference
            artwork_paths = {row['path'] for row in plan['original_artwork'].values()}

            def read_reference(reference):
                if reference['path'] in artwork_paths:
                    return Path(folder)/'marker.png'
                return original_read_reference(reference)

            # Isolate projection gating from the independent full-matrix and
            # installed-artwork checks; all evidence files and hashes stay real.
            with patch.object(sides, 'coverage', return_value={'fixture_complete': True}), \
                    patch.object(sides, 'read_reference', side_effect=read_reference):
                baseline = sides.analyze(plan_path, evidence_path)
                self.assertEqual(baseline['original_art']['status'], 'OBSERVED', baseline)
                self.assertTrue(baseline['visible_side_correctness_observed'])
                for moment in ('projection_before', 'projection_after'):
                    with self.subTest(moment=moment):
                        changed = deepcopy(evidence)
                        changed['states']['native'][moment]['screen'] = [579, 620]
                        evidence_path.write_text(json.dumps(changed), encoding='ascii')
                        result = sides.analyze(plan_path, evidence_path)
                        self.assertEqual(result['geometry']['native']['status'], 'FAIL')
                        self.assertEqual(result['original_art']['status'], 'FAIL')
                        self.assertFalse(result['original_art']['pairs'][0]['projections_stable'])
                        self.assertEqual(result['structural_status'], 'FAIL')
                        self.assertFalse(result['visible_side_correctness_observed'])
                changed = deepcopy(evidence)
                changed['states']['native']['projection_after']['screen'] = [579, 620]
                evidence_path.write_text(json.dumps(changed), encoding='ascii')
                with patch.object(sides, 'original_review', return_value={'status': 'OBSERVED'}):
                    result = sides.analyze(plan_path, evidence_path)
                    self.assertFalse(result['visible_side_correctness_observed'])

    def test_physical_candidates_require_actual_groups_including_support_baseline(self):
        with tempfile.TemporaryDirectory() as folder:
            plan_path, evidence_path, evidence = replay_fixture(Path(folder))
            evidence['evidence_kind'] = 'physical_native_capture'
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'captured applied owner groups: positive'):
                sides.analyze(plan_path, evidence_path)
            evidence['states']['positive'].pop('quantized_surfaces')
            evidence['states']['positive']['groups'] = [{'origin': [0, 0, 0], 'layer': 0,
                'uniforms': [[2047, 0, 0, 0], [45746, 45746, 0, 0], [0, 0, 0, 0], [39686, .45, 4159204, 1]],
                'texture': 'still_water_grey', 'template': None, 'visible': True}]
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'captured applied owner groups: negative'):
                sides.analyze(plan_path, evidence_path)
            evidence['states']['negative']['groups'] = []
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            result = sides.analyze(plan_path, evidence_path)
            self.assertEqual(result['structural_status'], 'OBSERVED')
            self.assertFalse(result['visible_side_correctness_observed'])

    def test_altered_png_and_incomplete_finite_batch_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            plan, evidence_path, evidence = replay_fixture(Path(folder))
            Image.fromarray(np.full((620, 580, 3), 255, np.uint8)).save(evidence['captures']['positive']['path'])
            result = sides.analyze(plan, evidence_path)
            self.assertTrue(result['capture_failures'])
            self.assertFalse(result['visible_side_correctness_observed'])
            evidence['captures'].pop('positive')
            evidence_path.write_text(json.dumps(evidence), encoding='ascii')
            result = sides.analyze(plan, evidence_path)
            self.assertTrue(any('finite capture set' in str(row) for row in result['capture_failures']))

    def test_support_baseline_cannot_change_source_topology(self):
        with tempfile.TemporaryDirectory() as folder:
            plan_path, _, _ = replay_fixture(Path(folder))
            plan = json.loads(plan_path.read_bytes())
            plan['declarations'][1]['source_cells'] = []
            with self.assertRaisesRegex(ValueError, 'exact source'):
                sides.validate_plan(plan)

    def test_cli_blocks_low_resolution_before_capture_and_keeps_output_immutable(self):
        with tempfile.TemporaryDirectory() as folder:
            directory = Path(folder)
            plan = {'schema': 1, 'kind': 'liquid_side_visible_v1', 'limits': sides.LIMITS,
                    'source_bindings': sides.source_bindings(),
                    'declarations': [declaration(sides.SOURCE_IDS[1], scale=100)]}
            plan_path, output_path = directory/'plan.json', directory/'offline-preflight.json'
            plan_path.write_text(json.dumps(plan), encoding='ascii')
            command = [sys.executable, str(ROOT/'tools/analyze_liquid_sides.py'),
                       '--plan', str(plan_path), '--output', str(output_path)]
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertTrue(output_path.is_file(), result.stderr)
            output = json.loads(output_path.read_bytes())
            self.assertFalse(output['preflight_geometry_ready'])
            self.assertFalse(output['visible_side_correctness_observed'])
            self.assertFalse(output['production_accepted'])
            frozen = sides.fingerprint(output_path)
            retry = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(retry.returncode, 2)
            self.assertEqual(sides.fingerprint(output_path), frozen)


if __name__ == '__main__':
    unittest.main()
