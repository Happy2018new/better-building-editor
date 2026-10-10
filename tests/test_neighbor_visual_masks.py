"""Camera uncertainty can exclude shared edges, not hidden-cell interiors."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from verify_context_batch_visuals import _roi_masks
from verify_missing_neighbor_visuals import compare_pixels
from PIL import Image, ImageDraw


class NeighborVisualMaskTests(unittest.TestCase):
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
