"""Deployment alpha replay fails closed on image, source and declared-control drift."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_liquid_deployment import analyze, PHASES


class LiquidDeploymentAnalysisTests(unittest.TestCase):
    def state(self, alpha, world):
        uniforms = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12], [2., alpha, .5, 1.]]
        if world:
            return {'liquid_groups': [{'key': 'liquid', 'id': 7,
                'group': ['key', 'model', [], uniforms]}], 'body_entity': 9,
                'body_parts': ['body'], 'body_uniforms': {'4': [1, 2, 3, 4]},
                'source_cells': [['position', 'waterlogged_fence']]}
        return {'liquid_groups': [{'key': 'liquid', 'model': 'model', 'model_ids': [7, 8],
            'front': 0, 'uniforms': uniforms}], 'document_id': 1, 'model_name': 'body',
            'tile_builds': 1, 'camera_pose': [0., 0., 3.], 'camera_pan': [.15, -.08],
            'screen_size': [120, 100], 'source_cells': [['position', 'waterlogged_fence']],
            'liquid_control_requests': [{'key': 'liquid', 'geometry': 'geometry', 'poses': ['pose'],
                'visible': [True], 'uniforms': [{'4': list(uniforms[3])}]}]}

    def fixture(self, directory):
        binding = {'owner': 'liquid', 'game_pid': 12, 'game_identity': 'identity', 'session_file': 'session'}
        regions = {'submerged_body': [[4, 4], [24, 24]], 'behind_block': [[88, 4], [108, 24]]}
        source = {'completed': True, 'restored': True, 'cleanup_errors': [], 'captures': {},
                  'session_binding': binding, 'scene': {'fence_rear': {}}, 'world': {'fence_rear': {}},
                  'transparency_plan': {'scene_engine_regions': regions, 'world_engine_regions': regions,
                      'scene_engine_screen': [120, 100], 'world_engine_screen': [120, 100]}}
        clear = np.repeat((40 + np.indices((100, 120))[1] % 5)[..., None], 3, axis=2)
        opaque = clear + 140
        for mode, prefix, world in (('editor', 'scene_fence_rear_', False),
                                    ('full', 'world_fence_rear_full_', True),
                                    ('missing', 'world_fence_rear_missing_', True)):
            states = {'baseline': self.state(-1., world)}
            target = source['world' if world else 'scene']['fence_rear']
            target[mode + '_water_alpha' if world else 'water_alpha'] = states
            for phase, alpha in PHASES.items():
                state = self.state(alpha, world)
                states[phase] = state if world else {'capture_state': state}
                label = prefix + 'water_alpha_' + phase
                values = np.rint(clear * (1. - (.45 if alpha == -1. else alpha))
                                 + opaque * (.45 if alpha == -1. else alpha)).astype(np.uint8)
                path = directory / (label + '.png')
                Image.fromarray(values).save(path)
                source['captures'][label] = dict(binding, path=str(path),
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest(), width=120, height=100,
                    ok=True, reliable=True, background_only=True, background_safe=True, native_resolution=True,
                    variance=[2., 2., 2.], backend='Windows.Graphics.Capture', frame={
                        'backend': 'Windows.Graphics.Capture', 'frame_qpc_100ns': 20, 'request_qpc_100ns': 10})
        return source

    def replay(self, directory, source):
        path = directory / 'source.json'
        path.write_text(json.dumps(source), encoding='ascii')
        return analyze(path)

    def test_three_routes_observe_alpha_without_promoting_uv_animation_or_production(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            result = self.replay(directory, self.fixture(directory))
            self.assertTrue(result['visible_alpha_qualified'])
            self.assertEqual(3, len(result['analyzer_sources']))
            self.assertEqual(3, len(result['routes']))
            self.assertFalse(result['side_uv_qualified'])
            self.assertFalse(result['animation_qualified'])
            self.assertFalse(result['production_qualified'])

    def test_capture_identity_staleness_or_cleanup_failure_prevents_qualification(self):
        for variant in ('identity', 'stale', 'cleanup'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                source = self.fixture(directory)
                capture = source['captures']['scene_fence_rear_water_alpha_0']
                if variant == 'identity':
                    capture['game_identity'] = 'different'
                elif variant == 'stale':
                    capture['frame']['frame_qpc_100ns'] = 9
                else:
                    source['cleanup_errors'].append('restore failed')
                self.assertFalse(self.replay(directory, source)['visible_alpha_qualified'])

    def test_unchanged_pixels_cannot_mask_source_or_applied_alpha_drift(self):
        for variant in ('source', 'alpha', 'native_alpha'):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                source = self.fixture(directory)
                state = source['scene']['fence_rear']['water_alpha']['0_45']['capture_state']
                if variant == 'source':
                    state['source_cells'] = []
                elif variant == 'alpha':
                    state['liquid_groups'][0]['uniforms'][3][1] = 1.
                else:
                    state['liquid_control_requests'][0]['uniforms'][0]['4'][1] = 1.
                self.assertFalse(self.replay(directory, source)['visible_alpha_qualified'])

    def test_nonlinear_intermediate_or_changed_default_fails_even_with_valid_png_receipt(self):
        for phase in ('0_45', 'default'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temporary:
                directory = Path(temporary)
                source = self.fixture(directory)
                row = source['captures']['world_fence_rear_missing_water_alpha_' + phase]
                values = np.asarray(Image.open(row['path'])).copy()
                values[4:24, 4:24] += 20
                Image.fromarray(values).save(row['path'])
                row['sha256'] = hashlib.sha256(Path(row['path']).read_bytes()).hexdigest()
                result = self.replay(directory, source)
                self.assertFalse(result['visible_alpha_qualified'])
                self.assertFalse(result['routes']['missing']['regions']['submerged_body']['passed'])

    def test_missing_controls_and_empty_or_single_region_cannot_vacuously_pass(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            source = self.fixture(directory)
            for regions in ({}, {'submerged_body': [[4, 4], [24, 24]]}):
                changed = copy.deepcopy(source)
                changed['transparency_plan']['scene_engine_regions'] = regions
                with self.assertRaisesRegex(ValueError, 'both declared submerged regions'):
                    self.replay(directory, changed)
            source['captures'].pop('scene_fence_rear_water_alpha_1')
            with self.assertRaisesRegex(ValueError, 'exactly twelve'):
                self.replay(directory, source)


if __name__ == '__main__':
    unittest.main()
