"""Visibility diagnostics must reject HUD-only and absent native references."""
from pathlib import Path
from copy import deepcopy
import json
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import analyze_liquid_native_write as analysis


class VisibilityTests(unittest.TestCase):
    def projection(self):
        return {'kind': 'affine', 'origin': [0, 0, 0],
                'affine': [[100, 0, 30, -240], [0, -100, 10, 560]],
                'toward': [-1, 1, -1], 'screen': [500, 500],
                'native_image_screen': [500, 500]}

    def test_masks_keep_support_water_separate_and_exclude_ui(self):
        masks = analysis.visibility_masks('water_depth_0_foreground', self.projection())
        self.assertFalse((masks['support'] & masks['water_envelope']).any())
        for mask in masks.values():
            self.assertGreater(mask.sum(), 80)
            self.assertFalse(mask[:60].any())
            self.assertFalse(mask[450:].any())
            self.assertFalse(mask[230:270, 230:270].any())

    def test_hud_changes_do_not_become_world_visibility(self):
        empty = np.full((500, 500, 3), 80, np.int16)
        image = empty.copy()
        image[:50] = 255
        image[455:] = 255
        image[230:270, 230:270] = 255
        row = analysis.measure(image, empty, analysis.visibility_masks(
            'water_depth_0_foreground', self.projection()))
        self.assertTrue(all(value['pixels'] == 0 and not value['observed'] for value in row.values()))

    def test_support_alone_does_not_establish_water_signal(self):
        empty = np.full((500, 500, 3), 80, np.int16)
        image = empty.copy()
        # Explicit physical support rectangle; this does not call the source mask.
        image[330:385, 80:170] = 180
        row = analysis.measure(image, empty, analysis.visibility_masks(
            'water_depth_0_foreground', self.projection()))
        self.assertTrue(row['support']['observed'])
        self.assertFalse(row['water_envelope']['observed'])

    def test_delta_twelve_does_not_pass_fixed_threshold(self):
        masks = {'support': np.ones((20, 20), bool), 'water_envelope': np.ones((20, 20), bool)}
        empty = np.zeros((20, 20, 3), np.int16)
        row = analysis.measure(empty + 12, empty, masks)
        self.assertTrue(all(value['pixels'] == 0 for value in row.values()))
        row = analysis.measure(empty + 13, empty, masks)
        self.assertTrue(all(value['observed'] for value in row.values()))

    def test_mismatched_viewport_rejected(self):
        with self.assertRaises(ValueError):
            analysis.measure(np.zeros((2, 2, 3)), np.zeros((3, 3, 3)), {})

    def test_camera_accepts_wrapped_and_bounded_rotation_only(self):
        expected = dict(position=[1, 2, 3], rotation=[2, -180, 0], screen=[500, 500], fov=60)
        wrapped = dict(expected, rotation=[2, 180, 360])
        self.assertTrue(analysis.camera_matches(wrapped, expected))
        self.assertTrue(analysis.camera_matches(dict(expected, rotation=[2 + .5e-6, -180, 0]), expected))
        self.assertFalse(analysis.camera_matches(dict(expected, rotation=[2 + 2.e-6, -180, 0]), expected))

    def test_complete_replay_requires_post_declaration_empty_and_native_pixels(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            projection = dict(self.projection(), position=[1, 2, 3], rotation=[2, -180, 0], fov=60)
            binding = dict(owner='fixture', game_pid=1, game_identity='fixture', session_file='fixture')
            declarations, captures, states = [], {}, {}
            empty = np.full((500, 500, 3), 80, np.int16)
            def capture(name, image):
                path = directory / (name + '.png')
                Image.fromarray(image.astype(np.uint8)).save(path)
                captures[name] = dict(analysis.reference(path), **binding, ok=True, reliable=True,
                    background_only=True, background_safe=True, native_resolution=True,
                    backend='Windows.Graphics.Capture', width=500, height=500, variance=[100, 100, 100],
                    frame=dict(backend='Windows.Graphics.Capture', frame_qpc_100ns=200, request_qpc_100ns=190))
            positions = [(3, 2, 3), (3, 3, 3)]
            def snapshot(source):
                cells = dict((tuple(pos), value) for pos, value in source)
                return {'valid': True, 'cells': [dict(pos=pos, foreground=cells.get(pos, ['minecraft:air', 0]),
                        background=['minecraft:air', 0], actor=False) for pos in positions]}
            camera = {key: projection[key] for key in ('position', 'rotation', 'screen', 'fov')}
            blank = dict(server=snapshot([]), client=snapshot([]), camera=camera)
            states['native_empty_vnw'] = {'before': deepcopy(blank), 'after': deepcopy(blank)}
            capture('native_empty_vnw', empty)
            for label, source in analysis.SOURCES.items():
                cells = analysis.sides.builtin_geometry(source)['source_cells']
                masks = analysis.visibility_masks(source, projection)
                # The complete replay checks evidence plumbing and diagnosis;
                # it is explicitly synthetic and establishes no native result.
                image = empty.copy()
                image[masks['support']] = [150, 150, 150]
                image[masks['water_envelope']] = [40, 100, 220]
                for route in analysis.ROUTES:
                    name = route + '_' + label
                    declarations.append(dict(id=name, source_id=source, source_cells=cells, projection=projection))
                    state = (dict(server=snapshot(cells), client=snapshot(cells), camera=camera)
                             if route.startswith('native') else dict(source_cells=cells, camera=camera))
                    states[name] = {'before': deepcopy(state), 'after': deepcopy(state)}
                    capture(name, image)
            plan_path = directory / 'geometry.json'
            plan_path.write_text(json.dumps(dict(kind='liquid_native_write_compare6', declarations=declarations,
                source_bindings={}, session_binding=binding, native_write_visibility=dict(
                    limits=analysis.LIMITS, analyzer=analysis.reference(analysis.__file__)))), encoding='ascii')
            source = dict(scope='H/L NW palette versus direct SetBlockNew native visibility diagnostic',
                preflight=dict(geometry_plan=analysis.reference(plan_path), created_qpc_100ns=100),
                session_binding=binding, captures=captures, states=states,
                completed=True, restored=True, cleanup_errors=[])
            path = directory / 'source.json'
            path.write_text(json.dumps(source), encoding='ascii')
            self.assertEqual('OBSERVED', analysis.analyze(path)['status'])
            capture('native_direct_h_vnw', empty)
            source['captures'] = captures
            path.write_text(json.dumps(source), encoding='ascii')
            self.assertEqual('FAIL', analysis.analyze(path)['status'])
            self.assertFalse(analysis.analyze(path)['native_visibility_observed'])
            captures['native_empty_vnw']['frame']['frame_qpc_100ns'] = 99
            captures['native_empty_vnw']['frame']['request_qpc_100ns'] = 98
            path.write_text(json.dumps(source), encoding='ascii')
            with self.assertRaisesRegex(ValueError, 'Empty capture precedes'):
                analysis.analyze(path)


if __name__ == '__main__':
    unittest.main()
