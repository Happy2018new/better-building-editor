"""Camera uncertainty can exclude shared edges, not hidden-cell interiors."""
import sys
import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_context_batch_visuals import _roi_masks
from verify_missing_neighbor_visuals import compare_pixels
import verify_neighbor_world_visuals as world
from PIL import Image, ImageDraw


class NeighborVisualMaskTests(unittest.TestCase):
    def calibrated_masks(self, session):
        keep, occupied = (0, 0, 0), (1, 0, 0)
        projection = {'projection_method': 'analytic_vertical_fov', 'fov': 60.,
                      'screen': (100, 80), 'position': (1., .5, -6.),
                      'target': (1., .5, 0.), 'rotation': (0., 0., 0.),
                      'runtime_minecraft_version': 'test-version', 'cells': []}
        for pos in (keep, occupied):
            projection['cells'].append({'pos': pos, 'world_points': [
                (pos[0] + dx, pos[1] + dy, pos[2] + dz)
                for dx in (0., 1.) for dy in (0., 1.) for dz in (0., 1.)]})
        calibration = {'passed': True, 'completed': True, 'session_file': session,
                       'runtime_minecraft_version': 'test-version', 'reported_fov': 60.,
                       'screen_aspect': 1.25, 'vertical_fov': 60.}
        return _roi_masks(projection, (100, 80), keep, occupied, calibration)

    @unittest.skipUnless(os.name == 'nt', 'Windows path equivalence')
    def test_calibration_accepts_windows_case_and_slash_variants(self):
        session = str((Path(__file__).resolve().parents[1] / 'owned-instance/session.json').resolve())
        for equivalent in (session, session.swapcase(), session.replace('\\', '/')):
            with self.subTest(path=equivalent), patch.dict(os.environ, MCDEV_SESSION_FILE=equivalent):
                keep, hidden, record = self.calibrated_masks(session)
                self.assertIsNotNone(keep.getbbox())
                self.assertIsNotNone(hidden.getbbox())
                self.assertEqual(60., record['projection']['effective_vertical_fov'])

    def test_calibration_rejects_another_or_missing_instance(self):
        for session in ('other-instance/session.json', ''):
            with self.subTest(path=session), patch.dict(os.environ, MCDEV_SESSION_FILE=session):
                with self.assertRaisesRegex(AssertionError, 'another instance'):
                    self.calibrated_masks('owned-instance/session.json')
        with patch.dict(os.environ, MCDEV_SESSION_FILE='owned-instance/session.json'):
            with self.assertRaisesRegex(AssertionError, 'another instance'):
                self.calibrated_masks('')

    def replay_calibration(self, calibration_session, expected_session):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            calibration = folder / 'calibration.json'
            evidence = folder / 'evidence.json'
            calibration.write_text(json.dumps({'session_file': calibration_session}), encoding='utf8')
            evidence.write_text(json.dumps({'session_file': expected_session}), encoding='utf8')
            argv = ['verify_neighbor_world_visuals.py', str(folder / 'output.json'),
                    '--camera-calibration', str(calibration), '--replay', str(evidence)]
            with patch.object(sys, 'argv', argv), patch.dict(os.environ), \
                    patch.object(world, 'replay', return_value=42) as replay:
                result = world.main()
                self.assertEqual(42, result)
                self.assertEqual(expected_session, os.environ['MCDEV_SESSION_FILE'])
                replay.assert_called_once()

    @unittest.skipUnless(os.name == 'nt', 'Windows path equivalence')
    def test_replay_accepts_windows_equivalent_session_paths(self):
        session = str((Path(__file__).resolve().parents[1] / 'owned-instance/session.json').resolve())
        self.replay_calibration(session.replace('\\', '/'), session.swapcase())

    def test_replay_rejects_calibration_from_another_instance(self):
        with self.assertRaisesRegex(AssertionError, 'another instance'):
            self.replay_calibration('other-instance/session.json', 'owned-instance/session.json')

    def test_guard_keeps_genuine_hidden_interior_residual_detectable(self):
        keep, occupied = (0, 0, 0), (1, 0, 0)
        projection = {'projection_method': 'native', 'fov': 60, 'screen': (100, 80),
                      'position': (0, 0, 6), 'target': (0, 0, 0), 'rotation': (0, 0, 0),
                      'cells': []}
        for pos, box in ((keep, (10, 20, 49, 59)), (occupied, (50, 20, 89, 59))):
            x0, y0, x1, y1 = box
            projection['cells'].append({'pos': pos, 'native_points': [
                {'screenX': x, 'screenY': y, 'isInScreen': True}
                for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]})
        keep_roi, hidden_roi, record = _roi_masks(projection, (100, 80), keep, occupied, boundary_guard=2)
        self.assertEqual(2, record['neighbor_boundary_guard_pixels'])
        self.assertEqual(0, hidden_roi.getpixel((51, 35)))
        self.assertEqual(255, hidden_roi.getpixel((70, 35)))
        baseline = Image.new('RGB', (100, 80))
        ImageDraw.Draw(baseline).rectangle((10, 20, 89, 59), fill=(150, 100, 60))
        edge_uncertainty = Image.new('RGB', baseline.size)
        ImageDraw.Draw(edge_uncertainty).rectangle((10, 20, 51, 59), fill=(150, 100, 60))
        genuine_residual = edge_uncertainty.copy()
        ImageDraw.Draw(genuine_residual).rectangle((70, 30, 80, 40), fill=(150, 100, 60))
        with tempfile.TemporaryDirectory() as directory:
            masks = keep_roi, hidden_roi
            correct = compare_pixels(baseline, edge_uncertainty, masks, Path(directory) / 'correct', 80, 16)
            incorrect = compare_pixels(baseline, genuine_residual, masks, Path(directory) / 'incorrect', 80, 16)
        self.assertTrue(correct['passed'], correct)
        self.assertTrue(incorrect['valid_baseline'], incorrect)
        self.assertTrue(incorrect['remaining_passed'], incorrect)
        self.assertFalse(incorrect['hidden_passed'], incorrect)
        self.assertGreater(incorrect['hidden_residual'], .05)
        self.assertIn('occupied_cell_native_pixels_remain', incorrect['failures'])


if __name__ == '__main__':
    unittest.main()
