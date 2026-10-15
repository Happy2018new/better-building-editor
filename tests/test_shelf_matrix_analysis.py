"""Shelf comparisons retain exterior drift without scoring it as shelf artwork."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from analyze_shelf_body_matrix_r20 import analyze, cell_scope, compare, oak_silhouette, pixels


class ShelfMatrixAnalysisTests(unittest.TestCase):
    def test_distant_scenery_does_not_change_scoped_shelf_score(self):
        empty = np.full((80, 90, 3), (80, 160, 220), dtype=np.uint8)
        native = empty.copy()
        native[20:65, 30:70] = (120, 70, 35)
        candidate = native.copy()
        candidate[:12, :20] = (0, 0, 0)
        scope = np.zeros((80, 90), dtype=bool)
        scope[18:68, 28:72] = True
        result = compare(native, candidate, empty, scope)
        self.assertEqual(1.0, result['unshifted_iou'])
        self.assertEqual(0.0, result['middle_raw_rmse'])
        self.assertEqual({'native': 0, 'candidate': 240}, result['changed_pixels_outside_scope'])
        self.assertEqual('native_projected_cell', result['scope'])

    def test_native_physical_corners_define_crop_scope_without_ui_rescaling(self):
        projection = {'isInScreen': True, 'screenX': 390., 'screenY': 370.}
        corners = [{'screen': {'isInScreen': True, 'screenX': x, 'screenY': y}}
                   for x in (230., 260.) for y in (240., 270.) for unused in range(2)]
        report = {'captures': {'oak_world': {'before': {'target_screen': projection}}}}
        case = {'label': 'oak', 'cell_projection': corners}
        scope = cell_scope(report, case, (300, 380, 3))
        self.assertTrue(scope[50, 45])
        self.assertFalse(scope[150, 145])
        self.assertFalse(scope[20, 20])
        corners[0]['screen']['isInScreen'] = False
        with self.assertRaises(ValueError):
            cell_scope(report, case, (300, 380, 3))

    def test_oak_chroma_diagnostic_rejects_background_shadow_and_missing_or_shifted_body(self):
        native = np.full((80, 90, 3), (80, 160, 220), dtype=np.uint8)
        native[20:65, 30:70] = (120, 90, 35)
        candidate = native.copy()
        scope = np.ones((80, 90), dtype=bool)
        candidate[:15, :20] = (40, 80, 110)
        self.assertEqual(1., oak_silhouette(native, candidate, scope)['unshifted_iou'])
        candidate[20:65, 30:70] = (80, 160, 220)
        missing = oak_silhouette(native, candidate, scope)
        self.assertEqual(0, missing['candidate_pixels'])
        self.assertEqual(0., missing['unshifted_iou'])
        candidate[20:65, 38:78] = (120, 90, 35)
        self.assertLess(oak_silhouette(native, candidate, scope)['unshifted_iou'], .8)
        with self.assertRaises(ValueError):
            oak_silhouette(candidate * 0, candidate, scope)

    def test_full_analysis_keeps_non_oak_samples_and_scopes_chroma_to_oak(self):
        with tempfile.TemporaryDirectory(prefix='shelf-matrix-') as temporary:
            directory = Path(temporary)
            empty = np.full((400, 500, 3), (80, 160, 220), dtype=np.uint8)
            body = empty.copy()
            body[150:250, 220:280] = (120, 90, 35)
            projection = {'isInScreen': True, 'screenX': 250., 'screenY': 200.}
            captures, cases = {}, []
            for wood in ('oak', 'birch'):
                label = wood + '_south'
                for suffix, array in (('world', body), ('empty', empty), ('unpowered', body)):
                    path = directory / (label + '_' + suffix + '.png')
                    Image.fromarray(array).save(path)
                    captures[label + '_' + suffix] = {
                        'path': str(path), 'reliable': True,
                        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                        'before': {'target_screen': projection}}
                cases.append({'label': label, 'material': {'name': 'minecraft:' + wood + '_shelf'},
                              'states': {}, 'cell_projection': [
                                  {'screen': {'isInScreen': True, 'screenX': x, 'screenY': y}}
                                  for x in (210., 290.) for y in (140., 260.) for unused in range(2)]})
            source = directory / 'report.json'
            source.write_text(json.dumps({'completed': True, 'restored': True, 'source_unchanged': True,
                                          'cleanup_errors': [], 'captures': captures, 'cases': cases}),
                              encoding='ascii')
            analyze(source, directory / 'review')
            result = json.loads((directory / 'review/review.json').read_bytes())
            self.assertIn('oak_silhouette_diagnostic', result['cases'][0]['scores']['unpowered'])
            self.assertNotIn('oak_silhouette_diagnostic', result['cases'][1]['scores']['unpowered'])
            self.assertTrue((directory / 'review/birch_south_unpowered.png').is_file())

    def test_portable_capture_sibling_is_authoritative_over_old_runtime_path(self):
        with tempfile.TemporaryDirectory(prefix='shelf-analysis-') as temporary:
            directory = Path(temporary)
            original = directory / 'old-runtime'
            packaged = directory / 'package'
            original.mkdir()
            packaged.mkdir()
            Image.new('RGB', (500, 400), (0, 0, 0)).save(original / 'frame.png')
            target = packaged / 'frame.png'
            Image.new('RGB', (500, 400), (180, 100, 50)).save(target)
            report = {'captures': {'sample': {
                'path': str(original / 'frame.png'), 'reliable': True,
                'sha256': hashlib.sha256(target.read_bytes()).hexdigest(),
                'before': {'target_screen': {'isInScreen': True, 'screenX': 250., 'screenY': 200.}}}}}
            result = pixels(report, 'sample', packaged)
            self.assertEqual((300, 380, 3), result.shape)
            self.assertEqual([180, 100, 50], result[0, 0].tolist())


if __name__ == '__main__':
    unittest.main()
