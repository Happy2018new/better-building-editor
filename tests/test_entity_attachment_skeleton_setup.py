"""Rejected skeleton replacement cannot become a subsequent item test."""
from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import probe_entity_attachment_capabilities as probe


class SkeletonSetup(unittest.TestCase):
    def test_only_nonnegative_integer_for_exact_model_passes(self):
        for identity in (-1, -2, None, False, True, '7', 7.5):
            with self.assertRaisesRegex(ValueError, 'SetModel failed'):
                probe.validate_skeleton_setup({'model': 'test-model', 'model_id': identity}, 'test-model')
        for identity in (0, 7):
            probe.validate_skeleton_setup({'model': 'test-model', 'model_id': identity}, 'test-model')
        with self.assertRaisesRegex(ValueError, 'SetModel failed'):
            probe.validate_skeleton_setup({'model': 'other-model', 'model_id': 7}, 'test-model')

    def test_native_rejection_is_preserved_then_exact_cleanup_runs_without_ui_or_bind(self):
        calls, reports = [], []
        setup = {'model': 'test-model', 'model_id': -1}
        camera = {'camera_pos': [1., 2., 3.], 'camera_rot': [0., 0., 0.],
                  'pitch_lock': False, 'yaw_lock': False}

        def execute(client, code):
            calls.append(code)
            if code == probe.SAVE:
                return {'saved': True, 'entities': {'anchor': 'owned-anchor'}}
            if 'SetModel(' in code:
                return setup
            if code == probe.RESTORE:
                return {'cleanup_completed': True, 'baseline': camera, 'restored': camera}
            self.fail('Rejected SetModel reached UI, binding or capture: ' + code)

        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / 'session.json'
            session.write_text('{}', encoding='ascii')
            argv = ['probe', '--session', str(session), '--owner', 'test-owner',
                    '--output', str(Path(directory) / 'result.json'), '--capture-exe', 'unused.exe',
                    '--skeleton-model', 'test-model']
            with patch.object(sys, 'argv', argv), patch.object(probe, 'load_session', return_value={'project': str(ROOT)}), \
                    patch.object(probe.base, 'Client', return_value=MagicMock()), \
                    patch.object(probe.base, 'run', side_effect=execute), \
                    patch.object(probe.base, 'write', side_effect=lambda path, report: reports.append(deepcopy(report))), \
                    patch.object(probe.base, 'capture') as capture, patch.dict(probe.os.environ):
                with self.assertRaisesRegex(ValueError, 'SetModel failed'):
                    probe.main()
                capture.assert_not_called()
        self.assertEqual(len(calls), 3)
        self.assertEqual(calls[-1], probe.RESTORE)
        self.assertEqual(reports[0]['skeleton_setup'], setup)
        self.assertEqual(reports[-1]['skeleton_setup'], setup)
        self.assertFalse(reports[-1]['completed'])
        self.assertTrue(reports[-1]['restored'])
        self.assertFalse(reports[-1]['production_rendering_accepted'])
        self.assertIn('SetModel failed', reports[-1]['error'])
